"""Assemble the multi-modal training corpus.

Composition of one sample:

    observed IMU = device( real UCI-HAR background  +  synthesised event physics )
    observed AUD = real ESC-50 cabin background     +  real crash / confuser audio
    observed GPS = kinematically consistent speed trace

The background is real recorded smartphone sensor data (noise floor, mounting
wobble, human motion); the event is physics. Neither alone is enough: pure
synthetic data has an unrealistically clean noise floor and models learn to
exploit it, while real data alone has no crashes in it.

The device model (sensors.apply_device_response) is applied LAST, so clipping
acts on the summed signal exactly as it would on a handset.
"""
from __future__ import annotations

import numpy as np

from ml.common.config import (
    AUDIO_LEN,
    DATA_PROC,
    GPS_IMPACT_IDX,
    GPS_LEN,
    IMU_HZ,
    SEED,
    STAGE_A_G,
    STAGE_A_MIN_SPEED_KMH,
    WIN_LEN,
)
from ml.crash_detection import audio_data, imu_data, synth
from ml.crash_detection.sensors import (
    apply_device_response,
    sample_device,
    saturation_features,
)

# Event mix. Heavily weighted toward the hard negatives, because the metric
# that matters is false positives per driving hour, not balanced accuracy.
MIX = {
    "CRASH": 0.26,
    "EMERGENCY_STOP": 0.14,   # the hard negative: crash-sized delta-V, no crash
    "HARD_BRAKE": 0.10,
    "POTHOLE": 0.12,
    "SPEED_BUMP": 0.07,
    "PHONE_DROP": 0.15,
    "DOOR_SLAM": 0.05,
    "ROUGH_ROAD": 0.06,
    "NORMAL_DRIVE": 0.05,
}

GPS_FEATURES = [
    "gps_v0", "gps_v_end", "gps_drop_kmh", "gps_drop_frac",
    "gps_max_decel_kmh_s", "gps_decel_ratio", "gps_v_min", "gps_settled",
]


def gps_features(v: np.ndarray) -> dict:
    """Kinematic descriptors. `gps_drop_kmh` is the delta-V the IMU lost to clipping."""
    pre = float(np.median(v[:GPS_IMPACT_IDX]))
    post = float(np.median(v[GPS_IMPACT_IDX + 2:])) if GPS_LEN > GPS_IMPACT_IDX + 2 else float(v[-1])
    d = np.diff(v)
    max_decel = float(-d.min()) if len(d) else 0.0
    # A crash dumps its speed in ~1 sample; braking spreads it over several.
    # This ratio is the single most discriminative GPS feature.
    total_drop = max(0.0, pre - post)
    ratio = max_decel / (total_drop + 1e-6) if total_drop > 1 else 0.0
    return {
        "gps_v0": pre,
        "gps_v_end": post,
        "gps_drop_kmh": total_drop,
        "gps_drop_frac": total_drop / (pre + 1e-6),
        "gps_max_decel_kmh_s": max_decel,
        "gps_decel_ratio": float(ratio),
        "gps_v_min": float(v.min()),
        "gps_settled": float(np.std(v[GPS_IMPACT_IDX + 2:]) if GPS_LEN > GPS_IMPACT_IDX + 2 else 0.0),
    }


def stage_a_pass(accel_obs: np.ndarray, v0_kmh: float) -> tuple[bool, bool]:
    """PRD 6.1.2 cheap gate, evaluated on clipped data as it would be on-device.

    Two configurations, because they behave very differently:

      full      |a| >= 4 g AND speed >= 20 km/h.  The speed pre-condition is
                what eliminates dropped phones.
      degraded  |a| >= 4 g only.  This is what actually runs whenever GPS is
                unavailable -- tunnels, urban canyons, cold start, indoors --
                which is common on exactly the rural and highway stretches the
                product targets. Here dropped phones DO reach the classifier
                and audio becomes the only defence.

    The model is trained on the degraded (superset) gate so it is correct in
    both regimes; both are reported at evaluation.
    """
    mag = np.linalg.norm(accel_obs, axis=1)
    thresh = bool(mag.max() >= STAGE_A_G)
    return thresh and bool(v0_kmh >= STAGE_A_MIN_SPEED_KMH), thresh


def partition_sources(bg_subj: np.ndarray, n_crash: int, n_esc: int,
                      seed: int = SEED, frac=(0.6, 0.2, 0.2)) -> dict:
    """The train/val/test partition of every repeated source, in one place.

    Factored out of `build()` so a second caller -- `export_deployable.py`'s
    equivalence check -- can regenerate the SAME held-out test clips, rather
    than re-deriving the split logic and risking a drift that would silently
    leak train-split audio into what is reported as a held-out verification.

    Uses its OWN generator seeded from `seed`, deliberately independent of
    whatever `rng` the caller is using for event generation. If this drew from
    a shared, already-advanced generator instead, reproducing the split would
    require replaying every prior draw in the exact same order -- fragile, and
    it would force `export_deployable.py` to redo the (slow) background
    reconstruction step purely to advance an RNG to the right position.
    Decoupled, the split is a pure function of `seed` and the source counts.
    """
    rng = np.random.default_rng(seed)

    def _part(n):
        idx = rng.permutation(n)
        a, b = int(n * frac[0]), int(n * (frac[0] + frac[1]))
        return {"train": idx[:a], "val": idx[a:b], "test": idx[b:]}

    subj_all = np.unique(bg_subj)
    sp = rng.permutation(len(subj_all))
    a, b = int(len(subj_all) * frac[0]), int(len(subj_all) * (frac[0] + frac[1]))
    subj_pool = {"train": set(subj_all[sp[:a]]), "val": set(subj_all[sp[a:b]]),
                 "test": set(subj_all[sp[b:]])}
    return {"subject": subj_pool, "crash": _part(n_crash), "esc": _part(n_esc)}


CHUNK = 512          # audio batch size for the mel/acoustic pass


def _flush(AUD, MEL, TAB, tab_start):
    """Compute mel + acoustic features for the buffered audio, then clear it."""
    if not AUD:
        return
    Y = np.asarray(AUD, dtype=np.float32)
    MEL.extend(audio_data.logmel_batch(Y))
    af = audio_data.acoustic_features_batch(Y)
    base = tab_start - 0            # TAB rows already appended for these clips
    for j in range(len(AUD)):
        row = TAB[base + j]
        for k, v in af.items():
            row[k] = float(v[j])
    AUD.clear()


def build(n: int = 24_000, seed: int = SEED, verbose: bool = True) -> dict:
    rng = np.random.default_rng(seed)

    if verbose:
        print("loading real backgrounds ...")
    bg_a, bg_g, bg_subj, bg_act = imu_data.build_continuous_backgrounds(
        WIN_LEN, rng, n_per_subject=260
    )
    crash_clips = audio_data.load_crash_clips()
    esc_clips, esc_cats = audio_data.load_esc50()

    # ---- split-disjoint pools -------------------------------------------
    # Every axis with repeated sources must be partitioned BEFORE generation:
    # HAR subjects (IMU background), crash recordings, and ESC-50 recordings.
    # Splitting only by subject after the fact leaves the same crash waveform
    # in train and test, and the audio branch memorises it.
    parts = partition_sources(bg_subj, len(crash_clips), len(esc_clips), seed)
    subj_pool, crash_pool, esc_pool = parts["subject"], parts["crash"], parts["esc"]

    mixers = {k: synth.AudioMixer(crash_clips, esc_clips, esc_cats, rng,
                                  crash_idx=crash_pool[k], esc_idx=esc_pool[k])
              for k in ("train", "val", "test")}
    if verbose:
        print(f"  split pools: crash clips "
              f"{ {k: len(v) for k, v in crash_pool.items()} }, "
              f"subjects { {k: len(v) for k, v in subj_pool.items()} }")
    if verbose:
        print(f"  IMU backgrounds {bg_a.shape}, subjects {len(np.unique(bg_subj))}")
        print(f"  crash audio {len(crash_clips)}, ESC-50 {len(esc_clips)}")

    # A phone in a moving vehicle is closest to the "still" HAR activities;
    # the walking classes stand in for a handheld / pocketed phone.
    still, moving = {}, {}
    for k, subs in subj_pool.items():
        insub = np.isin(bg_subj, list(subs))
        still[k] = np.where(insub & np.isin(bg_act, imu_data.STILL_ACTIVITIES))[0]
        moving[k] = np.where(insub & np.isin(bg_act, imu_data.MOTION_ACTIVITIES))[0]

    fold_names = np.array(["train", "val", "test"])
    fold_p = np.array([0.6, 0.2, 0.2])

    kinds = list(MIX)
    probs = np.array([MIX[k] for k in kinds], dtype=float)
    probs /= probs.sum()

    IMU, MEL, GPS, TAB, AUD = [], [], [], [], []
    y, sev, ev, subj, sa, sat_, dv, fold = [], [], [], [], [], [], [], []

    for i in range(n):
        if verbose and i % 3000 == 0:
            print(f"  {i}/{n}")
        fk = fold_names[rng.choice(3, p=fold_p)]
        mixer = mixers[fk]
        kind = kinds[rng.choice(len(kinds), p=probs)]
        e = synth.make_event(kind, rng)
        m = e["meta"]
        v0 = m["v0"]

        # Vehicle-borne events get a near-still background; a dropped phone is
        # usually being handled, so it gets the motion classes.
        pool = (moving if (kind == "PHONE_DROP" and rng.random() < 0.45) else still)[fk]
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
        f.update(gps_features(gps))
        f["gyro_peak_dps"] = float(np.abs(g_obs).max())
        f["gyro_integral_deg"] = float(np.abs(g_obs).sum() / IMU_HZ)

        IMU.append(np.concatenate([a_obs, g_obs, clip], axis=1))   # (WIN_LEN, 9)
        AUD.append(aud)
        GPS.append(gps.astype(np.float32))
        TAB.append(f)

        # Mel and acoustic features are computed in batches: one large BLAS
        # product instead of thousands of tiny ones (see logmel_batch).
        if len(AUD) >= CHUNK:
            _flush(AUD, MEL, TAB, len(MEL))

        y.append(m["label"])
        sev.append(m["severity"])
        ev.append(synth.EVENT_IDX[kind])
        subj.append(int(bg_subj[bi]))
        _full, _thr = stage_a_pass(a_obs, v0)
        sa.append(_full)
        sat_.append(_thr)
        dv.append(m.get("dv_kmh", 0.0))
        fold.append(fk)

    _flush(AUD, MEL, TAB, len(MEL))

    import pandas as pd
    tab = pd.DataFrame(TAB)
    out = {
        "imu": np.asarray(IMU, dtype=np.float32),
        "mel": np.asarray(MEL, dtype=np.float16)[..., None],   # 64x126 float16 keeps this cache ~300 MB
        "gps": np.asarray(GPS, dtype=np.float32),
        "tab": tab.values.astype(np.float32),
        "tab_cols": np.array(tab.columns.tolist()),
        "y": np.asarray(y, dtype=np.int32),
        "sev": np.asarray(sev, dtype=np.int32),
        "event": np.asarray(ev, dtype=np.int32),
        "subject": np.asarray(subj, dtype=np.int32),
        "stage_a": np.asarray(sa, dtype=bool),
        "stage_a_thresh": np.asarray(sat_, dtype=bool),
        "dv": np.asarray(dv, dtype=np.float32),
        "fold": np.asarray(fold),
    }
    np.savez_compressed(DATA_PROC / "crash_multimodal.npz", **out)
    return out


if __name__ == "__main__":
    d = build()
    import collections
    print("\n" + "=" * 68)
    print(f"imu {d['imu'].shape}  mel {d['mel'].shape}  gps {d['gps'].shape}  tab {d['tab'].shape}")
    print(f"positives {d['y'].sum()} / {len(d['y'])}")
    print(f"\nStage-A gate pass rate by event type:")
    for k, i in synth.EVENT_IDX.items():
        m = d["event"] == i
        if m.sum():
            print(f"  {k:14s} n={m.sum():5d}  stage-A pass {d['stage_a'][m].mean()*100:5.1f}%")
    print(f"\noverall Stage-A pass: {d['stage_a'].mean()*100:.1f}%")
    print(f"crash recall through Stage-A alone: "
          f"{d['stage_a'][d['y'] == 1].mean()*100:.1f}%")
    print(f"\ntabular features ({len(d['tab_cols'])}): {list(d['tab_cols'])}")
