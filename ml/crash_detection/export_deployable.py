"""Build, verify, and export the DEPLOYABLE crash model -- the artifact that
actually ships to Android.

`train.py` trains and evaluates on PRECOMPUTED mel spectrograms (librosa,
offline, stored in the corpus). The phone has no offline librosa: it has a
microphone. This module closes that gap by:

  1. Reassembling the trained graph with `mel_frontend.LogMelFrontend` in
     place of the precomputed mel input (model.build_deployable_model),
  2. baking every modality's normalisation into the graph (Normalize layers)
     so the on-device contract is "feed raw physical-unit sensor values", and
  3. VERIFYING the result on fresh, held-out audio before calling it correct.

Verification is not optional here. Two independent things could silently
break: the frontend's math could diverge from librosa (checked in
mel_frontend.py, in isolation), and reusing trained layers on a new graph
could be wired wrong (wrong branch, wrong order, forgotten normalisation --
easy mistakes that produce a model which runs without error and predicts
garbage). This module checks the thing that actually matters: does the
DEPLOYABLE model's predicted crash probability match the TRAINING model's,
on the same held-out event, end to end.

Verification audio is regenerated (not reused from the corpus) because the
corpus stores only the precomputed mel, not the raw waveform, to keep its
on-disk size manageable (see build_dataset.py's CHUNK/_flush batching). The
regeneration reuses the SAME held-out ('test') clip pools via
`build_dataset.partition_sources`, so no train-split audio leaks into this
check either.
"""
from __future__ import annotations

import json

import numpy as np
import tensorflow as tf
from tensorflow import keras

from ml.common.config import ARTIFACTS, AUDIO_LEN, REPORTS, SEED, WIN_LEN
from ml.crash_detection import audio_data, build_dataset, imu_data, synth
from ml.crash_detection.model import build_deployable_model, export_tflite
from ml.crash_detection.sensors import (
    apply_device_response,
    sample_device,
    saturation_features,
)


def _generate_verification_samples(n: int, seed: int, verbose: bool = True) -> dict:
    """Fresh synthetic events from the held-out ('test') source pools, keeping
    the raw audio waveform that the main corpus discards after computing mel.

    Deliberately reuses `synth.make_event`, `apply_device_response`,
    `sample_device`, `saturation_features`, `gps_features`, and
    `mixer.event` -- the exact physics and mixing code build_dataset.py runs
    -- so this can only diverge from the training corpus in HOW the samples
    are packaged (kept raw vs. batched into mel), never in what they represent.
    """
    rng = np.random.default_rng(seed + 777)   # distinct stream from generation
    if verbose:
        print(f"  regenerating {n} held-out verification samples ...")
    bg_a, bg_g, bg_subj, bg_act = imu_data.build_continuous_backgrounds(
        WIN_LEN, rng, n_per_subject=60)
    crash_clips = audio_data.load_crash_clips()
    esc_clips, esc_cats = audio_data.load_esc50()

    parts = build_dataset.partition_sources(bg_subj, len(crash_clips), len(esc_clips), seed)
    test_subj = parts["subject"]["test"]
    mixer = synth.AudioMixer(crash_clips, esc_clips, esc_cats, rng,
                             crash_idx=parts["crash"]["test"], esc_idx=parts["esc"]["test"])

    insub = np.isin(bg_subj, list(test_subj))
    still = np.where(insub & np.isin(bg_act, imu_data.STILL_ACTIVITIES))[0]
    moving = np.where(insub & np.isin(bg_act, imu_data.MOTION_ACTIVITIES))[0]

    kinds = list(build_dataset.MIX)
    probs = np.array([build_dataset.MIX[k] for k in kinds], dtype=float)
    probs /= probs.sum()

    IMU, RAW_AUD, MEL, GPS, TAB, Y = [], [], [], [], [], []
    for _ in range(n):
        kind = kinds[rng.choice(len(kinds), p=probs)]
        e = synth.make_event(kind, rng)
        m, v0 = e["meta"], e["meta"]["v0"]

        pool = moving if (kind == "PHONE_DROP" and rng.random() < 0.45) else still
        bi = pool[rng.integers(len(pool))]

        ideal_a = e["accel"] + bg_a[bi]
        ideal_g = e["gyro"] + bg_g[bi]
        if kind not in ("PHONE_DROP", "DOOR_SLAM"):
            ideal_a = ideal_a + synth._road_vibration(WIN_LEN, v0, rng.uniform(0.6, 3.0), rng)

        dev = sample_device(rng)
        a_obs, g_obs, clip = apply_device_response(ideal_a, ideal_g, dev, rng)
        gps = e["gps"]
        aud = mixer.event(e["audio"], v0)

        f = saturation_features(a_obs, clip, dev["accel_rail_g"])
        f.update(build_dataset.gps_features(gps))
        f.update(audio_data.acoustic_features(aud))
        f["gyro_peak_dps"] = float(np.abs(g_obs).max())
        f["gyro_integral_deg"] = float(np.abs(g_obs).sum())

        IMU.append(np.concatenate([a_obs, g_obs, clip], axis=1))
        RAW_AUD.append(aud)
        MEL.append(audio_data.logmel(aud))
        GPS.append(gps.astype(np.float32))
        TAB.append(f)
        Y.append(m["label"])

    import pandas as pd
    tab_df = pd.DataFrame(TAB)
    return {
        "imu": np.asarray(IMU, dtype=np.float32),
        "raw_audio": np.asarray(RAW_AUD, dtype=np.float32),
        "mel": np.asarray(MEL, dtype=np.float32)[..., None],
        "gps": np.asarray(GPS, dtype=np.float32),
        "tab": tab_df.values.astype(np.float32),
        "tab_cols": tab_df.columns.tolist(),
        "y": np.asarray(Y, dtype=np.int32),
    }


def verify_and_export(trained: keras.Model, norm_stats: dict, mel_frames: int,
                      n_tab: int, n_verify: int = 300, seed: int = SEED,
                      out_path=None) -> dict:
    """The full close-out for MVP-PLAN.md 4.1: build the deployable graph,
    verify it against the training model on fresh held-out events, export
    TFLite, and verify TFLite matches the deployable Keras model too.

    Raises AssertionError rather than returning a bad artifact if either
    check fails -- this is a gate, not a report.
    """
    v = _generate_verification_samples(n_verify, seed)

    deployable = build_deployable_model(trained, n_tab, mel_frames, norm_stats)

    # Path A: precomputed mel (what train.py evaluates), for the SAME events.
    def _norm(key, x):
        mu, sd = norm_stats[key]
        return (x - mu) / sd

    p_trained = trained.predict(
        {"imu": _norm("imu", v["imu"]), "mel": _norm("mel", v["mel"]),
         "gps": _norm("gps", v["gps"]), "tab": _norm("tab", v["tab"])},
        verbose=0)[0].ravel()

    # Path B: raw audio through the on-device frontend (what the phone runs).
    p_deploy = deployable.predict(
        {"imu": v["imu"], "raw_audio": v["raw_audio"], "gps": v["gps"], "tab": v["tab"]},
        verbose=0)[0].ravel()

    diff = np.abs(p_trained - p_deploy)
    result = {
        "n_verify": int(n_verify),
        "n_positive": int(v["y"].sum()),
        "prob_diff_mean": float(diff.mean()),
        "prob_diff_max": float(diff.max()),
        "prob_diff_p99": float(np.percentile(diff, 99)),
        "trained_decisions": int((p_trained >= 0.5).sum()),
        "deploy_decisions": int((p_deploy >= 0.5).sum()),
        "decision_agreement": float((( p_trained >= 0.5) == (p_deploy >= 0.5)).mean()),
    }

    # ---- export + verify the TFLite artifact matches the Keras graph ------
    out_path = out_path or (ARTIFACTS / "crash_fusion_deployable_v1.tflite")
    size = export_tflite(deployable, out_path)
    result["tflite_bytes"] = int(size)
    result["tflite_kb"] = round(size / 1024, 1)

    interp = tf.lite.Interpreter(model_path=str(out_path))
    interp.allocate_tensors()
    in_by_name = {d["name"].split(":")[0].split("serving_default_")[-1]: d
                 for d in interp.get_input_details()}
    out_details = interp.get_output_details()
    crash_out = next(d for d in out_details if d["shape"][-1] == 1)

    n_check = min(40, n_verify)
    inputs_by_key = {"imu": v["imu"], "raw_audio": v["raw_audio"],
                     "gps": v["gps"], "tab": v["tab"]}
    # Batch dimension is fixed at 1 by from_keras_model conversion, matching
    # every input array's per-sample shape already -- resize once, not per
    # sample, since it never actually changes across the loop.
    for key, arr in inputs_by_key.items():
        interp.resize_tensor_input(in_by_name[key]["index"], (1,) + arr.shape[1:])
    interp.allocate_tensors()

    tfl_probs = np.empty(n_check, dtype=np.float32)
    for i in range(n_check):
        for key, arr in inputs_by_key.items():
            interp.set_tensor(in_by_name[key]["index"], arr[i:i + 1])
        interp.invoke()
        tfl_probs[i] = interp.get_tensor(crash_out["index"]).ravel()[0]

    tflite_diff = np.abs(p_deploy[:n_check] - tfl_probs)
    result["tflite_vs_keras_max_diff"] = float(tflite_diff.max())
    result["tflite_vs_keras_mean_diff"] = float(tflite_diff.mean())

    print(f"  Keras deployable vs training model  (n={n_verify}, "
          f"{result['n_positive']} positive):")
    print(f"    prob diff  mean={result['prob_diff_mean']:.4f}  "
          f"max={result['prob_diff_max']:.4f}  p99={result['prob_diff_p99']:.4f}")
    print(f"    decision agreement: {result['decision_agreement']*100:.2f}%")
    print(f"  TFLite vs Keras deployable  (n={n_check}):")
    print(f"    prob diff  mean={result['tflite_vs_keras_mean_diff']:.5f}  "
          f"max={result['tflite_vs_keras_max_diff']:.5f}")
    print(f"  artifact: {out_path}  ({result['tflite_kb']} KB)")

    # Thresholds: decision agreement is the metric that actually matters (does
    # the phone fire when the trained model would have), set high because any
    # genuine wiring bug (wrong branch order, missing normalisation) produces
    # near-random agreement, not a small drop. The probability-diff bounds
    # catch a subtler regression even when the binary decision still matches.
    assert result["decision_agreement"] >= 0.97, (
        "deployable model disagrees with the trained model far more than "
        "frontend noise explains -- do not ship, inspect the graph wiring")
    assert result["prob_diff_mean"] < 0.05, "deployable model diverges on average"
    assert result["tflite_vs_keras_max_diff"] < 1e-3, "TFLite export diverges from Keras"

    return result


if __name__ == "__main__":
    # Standalone mode: reload the trained model from disk. Requires it was
    # saved with the current model.py (submodel-refactored) architecture --
    # run `python -m ml.crash_detection.train` first if artifacts predate it.
    import ml.crash_detection.mel_frontend  # noqa: F401  registers LogMelFrontend
    trained = keras.models.load_model(ARTIFACTS / "crash_fusion_v1.keras")
    z = np.load(ARTIFACTS / "crash_fusion_norm.npz")
    norm_stats = {k: (z[f"{k}_0"], z[f"{k}_1"]) for k in ("imu", "mel", "gps", "tab")}
    mel_frames = z["mel_0"].shape[2]
    n_tab = z["tab_0"].shape[1]

    result = verify_and_export(trained, norm_stats, mel_frames, n_tab)
    (REPORTS / "deployable_verification.json").write_text(json.dumps(result, indent=2))
    print("\nPASS: deployable model verified and exported.")
