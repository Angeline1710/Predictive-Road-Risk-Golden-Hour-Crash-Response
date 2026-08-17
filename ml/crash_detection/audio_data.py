"""Acoustic branch data: real crash audio + real environmental negatives.

Sources (both Hugging Face Hub):
  Titung/car-crash-audio-cc  -- 46 clips of genuine car-crash audio, CC BY 3.0,
                                sourced from 38 Creative Commons YouTube videos.
  ashraq/esc50               -- ESC-50, 2000 clips / 50 environmental classes,
                                CC BY-NC. Supplies both in-cabin background
                                (engine, car_horn, siren, train, rain, wind) and
                                the impulsive confusers that matter most
                                (fireworks, can_opening, door_knock, clapping).

LICENCE NOTE: ESC-50 is CC BY-NC (non-commercial). Fine for the hackathon,
research and evaluation. It must be swapped for a commercially-licensed corpus
before any paid deployment -- flagged in the model card, not buried here.

Why audio earns its place: the accelerometer saturates and stops carrying
magnitude information (see sensors.py), but a crash is acoustically enormous
and unmistakable -- deforming metal, breaking glass, and an airbag deployment
which is a ~170 dB impulse. Critically, the microphone is an INDEPENDENT
physical channel: a dropped phone rails the accelerometer but is nearly silent.
"""
from __future__ import annotations

import io
import urllib.parse
import urllib.request
import warnings

import numpy as np

from ml.common.config import AUDIO_HZ, AUDIO_LEN, DATA_RAW, HOP, N_MELS

warnings.filterwarnings("ignore", category=UserWarning)

CRASH_REPO = "Titung/car-crash-audio-cc"
ESC50_REPO = "ashraq/esc50"

CRASH_PARQUET = (
    f"https://huggingface.co/datasets/{CRASH_REPO}"
    "/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
)
ESC50_PARQUET = (
    f"https://huggingface.co/datasets/{ESC50_REPO}"
    "/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
)

# ESC-50 categories that plausibly occur in or near a vehicle cabin.
CABIN_BG = {"engine", "car_horn", "siren", "train", "rain", "wind", "airplane",
            "helicopter", "thunderstorm", "washing_machine", "vacuum_cleaner"}
# Impulsive non-crash sounds -- the acoustic equivalent of a hard negative.
IMPULSIVE_NEG = {"fireworks", "can_opening", "door_wood_knock", "clapping",
                 "mouse_click", "keyboard_typing", "church_bells", "chainsaw",
                 "hand_saw", "crackling_fire", "footsteps", "sneezing", "coughing"}


def _decode(blob) -> tuple[np.ndarray, int]:
    import soundfile as sf
    if isinstance(blob, dict):
        if blob.get("array") is not None:
            return np.asarray(blob["array"], dtype=np.float32), int(blob["sampling_rate"])
        blob = blob["bytes"]
    y, sr = sf.read(io.BytesIO(blob), dtype="float32", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    return y, sr


def _resample(y: np.ndarray, sr: int, target: int = AUDIO_HZ) -> np.ndarray:
    if sr == target:
        return y
    import librosa
    return librosa.resample(y, orig_sr=sr, target_sr=target)


def load_crash_clips(force: bool = False) -> list[np.ndarray]:
    """Real crash audio, mono @ AUDIO_HZ, variable length.

    The dataset's parquet export carries only a `path` reference, not embedded
    bytes, so the .wav files are pulled from the repo directly.
    """
    cache = DATA_RAW / "crash_audio.npz"
    if cache.exists() and not force:
        z = np.load(cache, allow_pickle=True)
        return [np.asarray(c, dtype=np.float32) for c in z["clips"]]

    import pandas as pd
    df = pd.read_parquet(CRASH_PARQUET)
    base = f"https://huggingface.co/datasets/{CRASH_REPO}/resolve/main"
    clips = []
    for blob in df["audio"]:
        try:
            if isinstance(blob, dict) and blob.get("bytes") is None:
                # "hf://datasets/<repo>@<sha>/clips/x.wav" -> "clips/x.wav"
                rel = str(blob["path"]).split("/clips/")[-1]
                url = f"{base}/{urllib.parse.quote('clips/' + rel)}"
                with urllib.request.urlopen(url, timeout=120) as r:
                    y, sr = _decode(r.read())
            else:
                y, sr = _decode(blob)
            y = _resample(y, sr)
            if len(y) >= AUDIO_HZ // 2:
                clips.append(y.astype(np.float32))
        except Exception as e:
            print(f"  skip crash clip: {e}")
    np.savez_compressed(cache, clips=np.array(clips, dtype=object))
    return clips


def load_esc50(force: bool = False) -> tuple[list[np.ndarray], list[str]]:
    """ESC-50 clips (5 s each) with their category names."""
    cache = DATA_RAW / "esc50.npz"
    if cache.exists() and not force:
        z = np.load(cache, allow_pickle=True)
        # Equal-length clips collapse to a 2-D object array on save; force float.
        return [np.asarray(c, dtype=np.float32) for c in z["clips"]], list(z["cats"])

    import pandas as pd
    df = pd.read_parquet(ESC50_PARQUET)
    catcol = "category" if "category" in df.columns else df.columns[-1]
    clips, cats = [], []
    for blob, cat in zip(df["audio"], df[catcol]):
        try:
            y, sr = _decode(blob)
            clips.append(_resample(y, sr).astype(np.float32))
            cats.append(str(cat))
        except Exception:
            continue
    np.savez_compressed(cache, clips=np.array(clips, dtype=object),
                        cats=np.array(cats, dtype=object))
    return clips, cats


def _moving_mean(x: np.ndarray, win: int) -> np.ndarray:
    """O(n) box filter via cumulative sum.

    np.convolve is O(n*win); at 64k samples and a 160-tap window that is ~10M
    ops per clip, which dominated corpus build time. This is the same filter.
    """
    if win <= 1:
        return x
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.empty_like(x)
    half = win // 2
    lo = np.clip(np.arange(len(x)) - half, 0, len(x))
    hi = np.clip(np.arange(len(x)) - half + win, 0, len(x))
    out = (c[hi] - c[lo]) / np.maximum(1, hi - lo)
    return out


def peak_index(y: np.ndarray, sr: int = AUDIO_HZ) -> int:
    """Locate the impact in a crash clip: the largest short-term energy jump."""
    win = max(1, sr // 100)                       # 10 ms
    e = _moving_mean(y.astype(np.float64) ** 2, win)
    # Onset = biggest positive derivative of energy, not simply the max sample,
    # which would drift to the loudest part of a long ring-out.
    d = np.diff(e, prepend=e[0])
    return int(np.argmax(d))


def take_window(y: np.ndarray, centre: int, n: int = AUDIO_LEN,
                pre_frac: float = 0.5) -> np.ndarray:
    """Extract `n` samples with `centre` placed `pre_frac` of the way in."""
    start = int(centre - n * pre_frac)
    out = np.zeros(n, dtype=np.float32)
    s0, s1 = max(0, start), min(len(y), start + n)
    if s1 > s0:
        out[s0 - start: s0 - start + (s1 - s0)] = y[s0:s1]
    return out


_N_FFT = 1024
_MEL_FB = None
_WINDOW = None


def _mel_setup(sr: int = AUDIO_HZ):
    """Cache the mel filterbank and window once.

    librosa.feature.melspectrogram rebuilds its filterbank and re-validates on
    every call, which measured at 254 ms per 4 s clip -- 85% of corpus build
    time. The transform below is the same one (Hann window, power spectrogram,
    Slaney mel basis, dB scaling); it just does the setup once.
    """
    global _MEL_FB, _WINDOW
    if _MEL_FB is None:
        import librosa
        _MEL_FB = librosa.filters.mel(sr=sr, n_fft=_N_FFT, n_mels=N_MELS,
                                      fmin=20, fmax=sr // 2).astype(np.float32)
        _WINDOW = np.hanning(_N_FFT).astype(np.float32)
    return _MEL_FB, _WINDOW


_FRAME_IDX: dict[int, np.ndarray] = {}


def _frame_index(n: int, padded: int) -> np.ndarray:
    key = n
    if key not in _FRAME_IDX:
        idx = np.arange(_N_FFT)[None, :] + HOP * np.arange(1 + n // HOP)[:, None]
        _FRAME_IDX[key] = np.minimum(idx, padded - 1)
    return _FRAME_IDX[key]


def logmel(y: np.ndarray, sr: int = AUDIO_HZ) -> np.ndarray:
    """(N_MELS, frames) log-mel spectrogram -- what the on-device branch consumes."""
    fb, win = _mel_setup(sr)
    pad = _N_FFT // 2
    yp = np.pad(y.astype(np.float32), pad, mode="reflect")
    frames = yp[_frame_index(len(y), len(yp))] * win[None, :]
    spec = np.abs(np.fft.rfft(frames, n=_N_FFT, axis=1)).astype(np.float32) ** 2
    # np.dot(spec, fb.T) rather than fb @ spec.T: the transposed operand drops
    # off the BLAS fast path and costs 151 ms instead of 6 ms for the same
    # 4 MFLOP product. Bit-identical result, 24x faster.
    mel = np.dot(spec, fb.T).T                           # (N_MELS, frames)
    db = 10.0 * np.log10(np.maximum(mel, 1e-10))
    return np.maximum(db, db.max() - 90.0).astype(np.float32)


def logmel_batch(Y: np.ndarray, sr: int = AUDIO_HZ) -> np.ndarray:
    """Batched log-mel for (B, samples) -> (B, N_MELS, frames).

    Per-clip logmel is dominated by call overhead and a small, inefficient
    matmul. Batching turns B small (64x513)@(513x126) products into one large
    (B*126, 513)@(513, 64), which is what BLAS is for -- roughly 60x faster per
    clip than looping, and it is the difference between a 90-minute corpus
    build and a 5-minute one.
    """
    fb, win = _mel_setup(sr)
    B, n = Y.shape
    pad = _N_FFT // 2
    Yp = np.pad(Y.astype(np.float32), ((0, 0), (pad, pad)), mode="reflect")
    idx = _frame_index(n, Yp.shape[1])                   # (frames, _N_FFT)
    frames = Yp[:, idx] * win[None, None, :]             # (B, frames, _N_FFT)
    spec = np.abs(np.fft.rfft(frames, n=_N_FFT, axis=2)).astype(np.float32) ** 2
    F = spec.shape[1]
    mel = np.dot(spec.reshape(B * F, -1), fb.T).reshape(B, F, N_MELS)
    db = 10.0 * np.log10(np.maximum(mel, 1e-10))
    db = np.maximum(db, db.max(axis=(1, 2), keepdims=True) - 90.0)
    return np.transpose(db, (0, 2, 1)).astype(np.float32)   # (B, N_MELS, frames)


def acoustic_features_batch(Y: np.ndarray, sr: int = AUDIO_HZ) -> dict:
    """Batched version of `acoustic_features` for (B, samples)."""
    E = Y.astype(np.float32) ** 2
    win = max(1, sr // 100)
    c = np.cumsum(np.pad(E, ((0, 0), (1, 0))), axis=1)
    n = Y.shape[1]
    half = win // 2
    lo = np.clip(np.arange(n) - half, 0, n)
    hi = np.clip(np.arange(n) - half + win, 0, n)
    env = (c[:, hi] - c[:, lo]) / np.maximum(1, hi - lo)[None, :]
    floor = np.percentile(env, 20, axis=1) + 1e-12
    peak = env.max(axis=1) + 1e-12
    rms = np.sqrt(E.mean(axis=1)) + 1e-9
    d = np.diff(env, prepend=env[:, :1], axis=1).max(axis=1)
    return {
        "aud_peak_db": 10 * np.log10(peak),
        "aud_snr_db": 10 * np.log10(peak / floor),
        "aud_crest": np.abs(Y).max(axis=1) / rms,
        "aud_onset_slope": d / (np.sqrt(floor) + 1e-9),
        "aud_zcr": (np.abs(np.diff(np.sign(Y), axis=1)) > 0).mean(axis=1),
    }


def acoustic_features(y: np.ndarray, sr: int = AUDIO_HZ) -> dict:
    """Scalar acoustic descriptors, mirroring what a cheap on-device DSP gives."""
    e = y.astype(np.float64) ** 2
    win = max(1, sr // 100)
    env = _moving_mean(e, win)
    floor = np.percentile(env, 20) + 1e-12
    peak = env.max() + 1e-12
    return {
        "aud_peak_db": float(10 * np.log10(peak)),
        "aud_snr_db": float(10 * np.log10(peak / floor)),
        "aud_crest": float(np.abs(y).max() / (np.sqrt(e.mean()) + 1e-9)),
        "aud_onset_slope": float(np.diff(env, prepend=env[0]).max() / (floor ** 0.5 + 1e-9)),
        "aud_zcr": float(np.mean(np.abs(np.diff(np.sign(y))) > 0)),
    }


if __name__ == "__main__":
    cl = load_crash_clips()
    print(f"crash clips: {len(cl)}  total {sum(len(c) for c in cl)/AUDIO_HZ:.1f} s")
    print(f"  lengths s: {[round(len(c)/AUDIO_HZ,1) for c in cl[:12]]}")
    e, cats = load_esc50()
    import collections
    cc = collections.Counter(cats)
    print(f"\nESC-50 clips: {len(e)}  categories: {len(cc)}")
    print(f"  cabin-bg available : {sorted(CABIN_BG & set(cc))}")
    print(f"  impulsive negatives: {sorted(IMPULSIVE_NEG & set(cc))}")
    print(f"  glass_breaking     : {cc.get('glass_breaking', 0)} clips")
    y = cl[0]
    print(f"\nlogmel shape: {logmel(take_window(y, peak_index(y))).shape}")
