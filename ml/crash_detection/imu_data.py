"""Real smartphone IMU backgrounds, from UCI HAR on the Hugging Face Hub.

Source: hf.co/datasets/udayl/UCI_HAR  (a full mirror of the original UCI
"Human Activity Recognition Using Smartphones" release, including the raw
`Inertial Signals/` folder).

Why this mirror and not one of the tidier parquet ones: the parquet mirrors
(e.g. pranavmr/UCI-HAR) are z-scored PER WINDOW. That normalisation makes every
activity have unit variance -- walking and lying down become numerically
identical -- which destroys exactly the amplitude information a crash detector
depends on. We need physical units, so we take the raw text signals.

Units in the raw release:
    body_acc_*   g  (gravity removed; this is Android's TYPE_LINEAR_ACCELERATION)
    total_acc_*  g  (gravity included)
    body_gyro_*  rad/s  -> converted to deg/s here
Sampled at 50 Hz in 128-sample (2.56 s) windows with 50% overlap.
"""
from __future__ import annotations

import io
import urllib.parse
import urllib.request

import numpy as np

from ml.common.config import DATA_RAW

REPO = "udayl/UCI_HAR"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main"

ACTIVITIES = {
    1: "WALKING",
    2: "WALKING_UPSTAIRS",
    3: "WALKING_DOWNSTAIRS",
    4: "SITTING",
    5: "STANDING",
    6: "LAYING",
}
# Activities we treat as "phone essentially still relative to its holder" --
# the best available proxy for a phone mounted or pocketed in a moving vehicle.
STILL_ACTIVITIES = (4, 5, 6)
MOTION_ACTIVITIES = (1, 2, 3)

RAD2DEG = 57.29577951308232


def _fetch(path: str) -> np.ndarray:
    url = f"{BASE}/{urllib.parse.quote(path)}"
    with urllib.request.urlopen(url, timeout=180) as r:
        raw = r.read()
    return np.loadtxt(io.BytesIO(raw), dtype=np.float32)


def download(force: bool = False) -> dict:
    """Fetch and cache the raw inertial signals. Returns arrays in physical units."""
    cache = DATA_RAW / "uci_har_raw.npz"
    if cache.exists() and not force:
        z = np.load(cache)
        return {k: z[k] for k in z.files}

    out = {}
    for split, tag in (("train", "train"), ("test", "test")):
        acc = np.stack(
            [_fetch(f"{split}/Inertial Signals/body_acc_{ax}_{tag}.txt") for ax in "xyz"],
            axis=-1,
        )  # (N, 128, 3) in g
        gyr = np.stack(
            [_fetch(f"{split}/Inertial Signals/body_gyro_{ax}_{tag}.txt") for ax in "xyz"],
            axis=-1,
        ) * RAD2DEG  # (N, 128, 3) in deg/s
        y = _fetch(f"{split}/y_{tag}.txt").astype(int)
        subj = _fetch(f"{split}/subject_{tag}.txt").astype(int)
        out[f"{split}_acc"] = acc.astype(np.float32)
        out[f"{split}_gyro"] = gyr.astype(np.float32)
        out[f"{split}_y"] = y
        out[f"{split}_subject"] = subj

    np.savez_compressed(cache, **out)
    return out


def load_all() -> dict:
    """All windows concatenated, with subject ids preserved for grouped splits."""
    d = download()
    return {
        "acc": np.concatenate([d["train_acc"], d["test_acc"]]),
        "gyro": np.concatenate([d["train_gyro"], d["test_gyro"]]),
        "y": np.concatenate([d["train_y"], d["test_y"]]),
        "subject": np.concatenate([d["train_subject"], d["test_subject"]]),
    }


def build_continuous_backgrounds(
    win_len: int,
    rng: np.random.Generator,
    n_per_subject: int = 400,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Stitch 128-sample HAR windows into longer continuous backgrounds.

    Model A needs 200-sample (4 s) windows; HAR ships 128-sample (2.56 s) ones.
    We concatenate consecutive windows from the same subject and activity --
    which are genuinely contiguous in the original recording, since UCI HAR
    windows are sequential with 50% overlap -- then cut `win_len` slices.

    Returns (acc, gyro, subject, activity) with acc/gyro shaped (N, win_len, 3).
    """
    d = load_all()
    acc, gyr, y, subj = d["acc"], d["gyro"], d["y"], d["subject"]

    A, G, S, Y = [], [], [], []
    for s in np.unique(subj):
        for a in np.unique(y):
            idx = np.where((subj == s) & (y == a))[0]
            if len(idx) < 3:
                continue
            # Windows overlap 50%, so take the second half of each to rebuild
            # a non-duplicated continuous stream.
            stream_a = np.concatenate([acc[i, 64:] for i in idx], axis=0)
            stream_g = np.concatenate([gyr[i, 64:] for i in idx], axis=0)
            if len(stream_a) < win_len + 1:
                continue
            n = min(n_per_subject, len(stream_a) - win_len)
            starts = rng.integers(0, len(stream_a) - win_len, size=n)
            for st in starts:
                A.append(stream_a[st: st + win_len])
                G.append(stream_g[st: st + win_len])
                S.append(s)
                Y.append(a)

    return (
        np.asarray(A, dtype=np.float32),
        np.asarray(G, dtype=np.float32),
        np.asarray(S, dtype=int),
        np.asarray(Y, dtype=int),
    )


if __name__ == "__main__":
    d = download()
    for k, v in d.items():
        print(f"{k:16s} {v.shape} {v.dtype}")
    acc = d["train_acc"]
    print("\nbody_acc (g): min %.3f max %.3f std %.4f" % (acc.min(), acc.max(), acc.std()))
    y = d["train_y"]
    for k, name in ACTIVITIES.items():
        m = y == k
        if m.sum():
            mag = np.linalg.norm(acc[m], axis=2)
            print(f"  {name:20s} n={m.sum():5d}  mean|a|={mag.mean():.4f} g  p99={np.percentile(mag,99):.4f} g")
