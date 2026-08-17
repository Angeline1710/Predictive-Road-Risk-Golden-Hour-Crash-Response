"""Train and evaluate CrashFusionNet.

Evaluation protocol, and why each choice is made:

SPLIT -- assigned at GENERATION time, disjoint on three axes simultaneously:
    the UCI-HAR subject supplying the IMU background (30 people), the crash
    recording supplying the impact audio (46 clips from 38 videos), and the
    ESC-50 recording supplying background and confuser audio. Any one of these
    shared across the split leaks: with 46 crash waveforms reused between train
    and test, an audio-only CNN memorises them and scores PR-AUC 1.000. The
    positive audio corpus is small, so test only ever sees ~10 unseen crash
    recordings -- that is a real limit on what these numbers can claim, and it
    is reported rather than engineered away.

GATE -- the model only ever sees windows that pass Stage-A, because that is
    all it sees on-device. Training on the full pool would teach it to
    separate crashes from parked cars, which is not the job.

METRICS -- recall at a FIXED false-positive budget, not accuracy and not
    threshold-free AUC alone. The operating point is chosen on validation to
    hold false positives per 100 driving hours under target, then recall is
    read off at that point on test. That mirrors the real cost asymmetry: a
    missed crash is a death, a false positive is a wasted ambulance.

ABLATION -- every unimodal baseline is trained under the identical protocol,
    so the fusion gain is attributable to fusion and not to capacity or tuning.
"""
from __future__ import annotations

import json
import time

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

from ml.common.config import ARTIFACTS, DATA_PROC, REPORTS, SEED, SEVERITY
from ml.crash_detection import synth
from ml.crash_detection.model import build_model, build_unimodal, export_tflite

# How much wall-clock driving one Stage-A-passing negative window represents.
# Calibrated from the generator's event mix: potholes/bumps/drops of this
# severity are assumed to occur at roughly the rates below during ordinary use.
# Used only to express the FP rate in an interpretable unit.
NEG_EVENTS_PER_DRIVING_HOUR = 12.0
FP_BUDGET_PER_100H = 1.0          # PRD 7.1 target


def load(gate: str = "degraded"):
    z = np.load(DATA_PROC / "crash_multimodal.npz", allow_pickle=True)
    d = {k: z[k] for k in z.files}
    m = d["stage_a_thresh"] if gate == "degraded" else d["stage_a"]
    keep = np.where(m)[0]
    out = {k: (v[keep] if isinstance(v, np.ndarray) and v.shape[:1] == (len(m),) else v)
           for k, v in d.items()}
    out["mel"] = out["mel"].astype(np.float32)
    return out


def preassigned_split(fold: np.ndarray):
    """Use the split assigned at generation time.

    The split cannot be made here. Disjointness is required on three axes at
    once -- HAR subject, crash recording, and ESC-50 recording -- and only the
    generator knows which source each sample was drawn from. Splitting after
    the fact by subject alone leaves the same 46 crash waveforms on both sides,
    which is what produced PR-AUC 1.000 for an audio-only baseline.
    """
    return (np.where(fold == "train")[0], np.where(fold == "val")[0],
            np.where(fold == "test")[0])


def norm_stats(X: np.ndarray, axis=0):
    mu = X.mean(axis=axis, keepdims=True)
    sd = X.std(axis=axis, keepdims=True) + 1e-6
    return mu, sd


def inputs(d, idx, st):
    imu = (d["imu"][idx] - st["imu"][0]) / st["imu"][1]
    mel = (d["mel"][idx] - st["mel"][0]) / st["mel"][1]
    gps = (d["gps"][idx] - st["gps"][0]) / st["gps"][1]
    tab = (d["tab"][idx] - st["tab"][0]) / st["tab"][1]
    return {"imu": imu, "mel": mel, "gps": gps, "tab": tab}


def fp_per_100h(n_fp: int, n_neg: int) -> float:
    """Convert a false-positive count into FPs per 100 driving hours."""
    if n_neg == 0:
        return float("nan")
    hours = n_neg / NEG_EVENTS_PER_DRIVING_HOUR
    return n_fp / hours * 100.0


def threshold_for_budget(y: np.ndarray, p: np.ndarray,
                         budget: float = FP_BUDGET_PER_100H) -> float:
    """Lowest threshold whose FP rate stays inside the budget (max recall)."""
    neg = p[y == 0]
    n_neg = len(neg)
    if n_neg == 0:
        return 0.5
    allowed = max(0, int(np.floor(budget / 100.0 * n_neg / NEG_EVENTS_PER_DRIVING_HOUR)))
    order = np.sort(neg)[::-1]
    if allowed >= n_neg:
        return 0.0
    # Just above the (allowed+1)-th highest negative score.
    return float(min(1.0, order[allowed] + 1e-6))


def evaluate(y, p, sev_true=None, sev_pred=None, thr=0.5, tag="") -> dict:
    yhat = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    r = {
        "tag": tag,
        "n": int(len(y)),
        "n_pos": int(y.sum()),
        "threshold": float(thr),
        "recall": float(tp / max(1, tp + fn)),
        "precision": float(tp / max(1, tp + fp)),
        "specificity": float(tn / max(1, tn + fp)),
        "pr_auc": float(average_precision_score(y, p)) if y.sum() else float("nan"),
        "roc_auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else float("nan"),
        "brier": float(brier_score_loss(y, p)),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "fp_per_100h": fp_per_100h(int(fp), int(tn + fp)),
    }
    if sev_true is not None and sev_pred is not None:
        m = y == 1
        if m.sum():
            r["severity_macro_f1"] = float(
                f1_score(sev_true[m], sev_pred[m], average="macro", labels=range(len(SEVERITY)),
                         zero_division=0))
    return r


def run(gate: str = "degraded", epochs: int = 40, seed: int = SEED) -> dict:
    tf.keras.utils.set_random_seed(seed)
    d = load(gate)
    tr, va, te = preassigned_split(d["fold"])
    print(f"[{gate}] n={len(d['y'])}  train={len(tr)} val={len(va)} test={len(te)}")
    print(f"  positives  train={d['y'][tr].sum()} val={d['y'][va].sum()} test={d['y'][te].sum()}")

    st = {k: norm_stats(d[k][tr]) for k in ("imu", "mel", "gps", "tab")}
    Xtr, Xva, Xte = inputs(d, tr, st), inputs(d, va, st), inputs(d, te, st)
    ytr, yva, yte = d["y"][tr], d["y"][va], d["y"][te]
    # Negatives take the explicit NONE class (index len(SEVERITY)).
    NONE = len(SEVERITY)
    sev_all = np.where(d["y"] == 1, d["sev"], NONE)
    str_, sva, ste = sev_all[tr], sev_all[va], sev_all[te]

    mel_frames = d["mel"].shape[2]
    model = build_model(d["tab"].shape[1], mel_frames)
    n_params = model.count_params()

    cb = [
        tf.keras.callbacks.EarlyStopping(monitor="val_crash_auc", mode="max",
                                         patience=8, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_crash_auc", mode="max",
                                             factor=0.5, patience=4, min_lr=1e-5),
    ]
    t0 = time.time()
    model.fit(Xtr, {"crash": ytr, "severity": str_},
              validation_data=(Xva, {"crash": yva, "severity": sva}),
              epochs=epochs, batch_size=64, callbacks=cb, verbose=2)
    train_s = time.time() - t0

    pv = model.predict(Xva, verbose=0)[0].ravel()
    thr = threshold_for_budget(yva, pv)
    pt, sevp = model.predict(Xte, verbose=0)
    pt = pt.ravel()

    res = {"gate": gate, "params": int(n_params), "train_seconds": round(train_s, 1),
           "fusion": evaluate(yte, pt, ste, sevp.argmax(1), thr, "fusion")}

    # ---- per-event-type false positive breakdown -------------------------
    ev_te = d["event"][te]
    per_event = {}
    for name, i in synth.EVENT_IDX.items():
        m = ev_te == i
        if m.sum() == 0:
            continue
        fired = (pt[m] >= thr)
        per_event[name] = {"n": int(m.sum()),
                           "fire_rate": float(fired.mean()),
                           "is_positive": name in synth.POSITIVE}
    res["per_event"] = per_event

    # ---- recall by crash severity ---------------------------------------
    dv_te = d["dv"][te]
    by_dv = {}
    for lo, hi in [(8, 18), (18, 30), (30, 48), (48, 80)]:
        m = (yte == 1) & (dv_te >= lo) & (dv_te < hi)
        if m.sum():
            by_dv[f"{lo}-{hi}"] = {"n": int(m.sum()),
                                   "recall": float((pt[m] >= thr).mean())}
    res["recall_by_delta_v"] = by_dv

    # ---- modality-ablation at inference: what if a sensor is missing? ----
    # Zeroing an input reproduces exactly what ModalityDropout trained for.
    degrade = {}
    for missing in ([], ["mel"], ["gps"], ["mel", "gps"], ["imu"]):
        Xm = {k: (np.zeros_like(v) if k in missing else v) for k, v in Xte.items()}
        pm = model.predict(Xm, verbose=0)[0].ravel()
        key = "all" if not missing else "no_" + "_".join(missing)
        degrade[key] = evaluate(yte, pm, thr=thr, tag=key)
    res["inference_degradation"] = degrade

    # ---- baselines, identical protocol ------------------------------------
    # NOTE `tab` is NOT a unimodal baseline: the 26 handcrafted scalars span
    # all three sensors (saturation + kinematic + acoustic). It is reported as
    # a HANDCRAFTED-FUSION baseline -- the "could you skip deep learning
    # entirely?" comparison -- and the per-modality tabular subsets are
    # reported separately so the ablation stays honest.
    base = {}
    tab_cols = [str(c) for c in d["tab_cols"]]
    sub = {"tab_imu": [i for i, c in enumerate(tab_cols)
                       if c.startswith(("sat_", "imu_", "gyro_"))],
           "tab_gps": [i for i, c in enumerate(tab_cols) if c.startswith("gps_")],
           "tab_aud": [i for i, c in enumerate(tab_cols) if c.startswith("aud_")]}
    for name, cols in sub.items():
        tf.keras.utils.set_random_seed(seed)
        um = build_unimodal("tab", len(cols), mel_frames)
        um.fit(Xtr["tab"][:, cols], ytr, validation_data=(Xva["tab"][:, cols], yva),
               epochs=epochs, batch_size=64, verbose=0,
               callbacks=[tf.keras.callbacks.EarlyStopping(
                   monitor="val_auc", mode="max", patience=8,
                   restore_best_weights=True)])
        pvb = um.predict(Xva["tab"][:, cols], verbose=0).ravel()
        tb = threshold_for_budget(yva, pvb)
        ptb = um.predict(Xte["tab"][:, cols], verbose=0).ravel()
        base[name] = evaluate(yte, ptb, thr=tb, tag=name)
        base[name]["n_features"] = len(cols)

    for which, key in (("imu", "imu"), ("audio", "mel"), ("gps", "gps"),
                       ("tab_all_handcrafted", "tab")):
        tf.keras.utils.set_random_seed(seed)
        um = build_unimodal("tab" if which.startswith("tab") else which,
                            d["tab"].shape[1], mel_frames)
        um.fit(Xtr[key], ytr, validation_data=(Xva[key], yva),
               epochs=epochs, batch_size=64, verbose=0,
               callbacks=[tf.keras.callbacks.EarlyStopping(
                   monitor="val_auc", mode="max", patience=8,
                   restore_best_weights=True)])
        pvb = um.predict(Xva[key], verbose=0).ravel()
        tb = threshold_for_budget(yva, pvb)
        ptb = um.predict(Xte[key], verbose=0).ravel()
        base[which] = evaluate(yte, ptb, thr=tb, tag=which)
        base[which]["params"] = int(um.count_params())
    res["unimodal"] = base

    # ---- export ----------------------------------------------------------
    if gate == "degraded":
        size = export_tflite(model, ARTIFACTS / "crash_fusion_v1.tflite")
        res["tflite_bytes"] = int(size)
        res["tflite_kb"] = round(size / 1024, 1)
        model.save(ARTIFACTS / "crash_fusion_v1.keras")
        np.savez(ARTIFACTS / "crash_fusion_norm.npz",
                 **{f"{k}_{i}": st[k][i] for k in st for i in (0, 1)})

        # The precomputed-mel model above is what gets EVALUATED (it is what
        # the corpus and this whole training loop are built around), but it is
        # NOT what ships -- the phone has a microphone, not offline librosa.
        # This builds, verifies against fresh held-out audio, and exports the
        # actual deployable artifact. See export_deployable.py and
        # MVP-PLAN.md 4.1 for why this step exists and what it closes.
        from ml.crash_detection.export_deployable import verify_and_export
        print("\n  building + verifying deployable (raw-audio) model ...")
        res["deployable"] = verify_and_export(
            model, st, mel_frames, d["tab"].shape[1],
            out_path=ARTIFACTS / "crash_fusion_deployable_v1.tflite")
    return res


if __name__ == "__main__":
    out = {}
    for gate in ("degraded", "full"):
        out[gate] = run(gate)
    (REPORTS / "crash_detection_results.json").write_text(json.dumps(out, indent=2))
    print("\n" + "=" * 72)
    for gate, r in out.items():
        f = r["fusion"]
        print(f"\n[{gate}]  params={r['params']:,}  " +
              (f"tflite={r.get('tflite_kb','-')} KB" if 'tflite_kb' in r else ""))
        print(f"  recall={f['recall']:.3f}  precision={f['precision']:.3f}  "
              f"PR-AUC={f['pr_auc']:.3f}  FP/100h={f['fp_per_100h']:.2f}")
        print("  unimodal PR-AUC: " + "  ".join(
            f"{k}={v['pr_auc']:.3f}" for k, v in r["unimodal"].items()))
