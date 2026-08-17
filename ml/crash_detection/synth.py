"""Coherent multi-modal event generator.

Each event emits IMU, audio and GPS that describe the SAME physical incident.
That coupling is the whole point of the fusion model, because each modality
covers a blind spot of the others:

    IMU    fast (50 Hz) and high-resolution, but SATURATES in a real crash,
           so it cannot measure how big the crash was.
    GPS    slow (1 Hz), cannot see the ~120 ms pulse at all, but measures the
           delta-V directly and unambiguously -- exactly what the railed
           accelerometer lost.
    AUDIO  independent physical channel. Separates "a large deceleration"
           from "a large deceleration accompanied by destruction". A hard
           brake and a 40 km/h barrier hit look similar to a clipped IMU and
           to 1 Hz GPS; they sound nothing alike.

Event taxonomy (labels: 1 = crash, 0 = not):
    CRASH          delta-V 8-80 km/h, pulse + ring-down, real crash audio,
                   GPS speed collapse
    EMERGENCY_STOP panic braking from highway speed to a standstill, often
                   with a kerb or verge strike at the end. Produces a GPS speed
                   collapse of the SAME magnitude as a crash. Deliberately
                   included so that "speed dropped a lot" cannot by itself
                   classify -- the model must use HOW the speed fell (one
                   sample vs a ramp) plus audio and the IMU pulse shape.
    HARD_BRAKE     smooth 0.6-0.9 g decel over 1.5-4 s, no clipping, tyre
                   squeal at most, smooth GPS ramp        <- the classic FP
    POTHOLE        3-12 g vertical spike, ~40 ms, may clip Z only, thump,
                   GPS unchanged
    SPEED_BUMP     two smaller paired spikes at survey speed
    PHONE_DROP     8-40 g multi-axis spike, may clip, clatter, GPS ~0
                   (this is the FP that pure-IMU detectors cannot reject)
    DOOR_SLAM      2-6 g, loud, GPS 0
    ROUGH_ROAD     sustained vibration, no discrete event
    NORMAL_DRIVE   background only
"""
from __future__ import annotations

import numpy as np

from ml.common.config import (
    AUDIO_HZ,
    AUDIO_LEN,
    GPS_IMPACT_IDX,
    GPS_LEN,
    IMPACT_IDX,
    IMU_HZ,
    SEVERITY_DV_BANDS,
    WIN_LEN,
)
from ml.crash_detection.sensors import crash_pulse, ringdown

EVENTS = [
    "CRASH",
    "EMERGENCY_STOP",
    "HARD_BRAKE",
    "POTHOLE",
    "SPEED_BUMP",
    "PHONE_DROP",
    "DOOR_SLAM",
    "ROUGH_ROAD",
    "NORMAL_DRIVE",
]
EVENT_IDX = {e: i for i, e in enumerate(EVENTS)}
POSITIVE = {"CRASH"}


def severity_from_dv(dv_kmh: float) -> int:
    for i, (lo, hi) in enumerate(SEVERITY_DV_BANDS):
        if lo <= dv_kmh < hi:
            return i
    return len(SEVERITY_DV_BANDS) - 1 if dv_kmh >= SEVERITY_DV_BANDS[-1][0] else 0


def _halfsine(k: int, peak: float) -> np.ndarray:
    """Half-sine transient sampled at bin MIDPOINTS.

    Using np.linspace(0, 1, k) endpoint-inclusive puts samples exactly on
    sin(0) and sin(pi) -- both zero -- so a k=2 transient silently becomes all
    zeros. Short impacts (a dropped phone contacts for ~10 ms = 0.5 samples at
    50 Hz) are precisely the case that hits. Midpoint sampling also models the
    real aliasing honestly: the sample lands somewhere inside the impact and
    captures a fraction of its peak.
    """
    t = (np.arange(k) + 0.5) / k
    return peak * np.sin(np.pi * t)


def _rot(rng: np.random.Generator) -> np.ndarray:
    """Random 3-D rotation: the phone's orientation in the cabin is unknown."""
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def _road_vibration(n: int, speed_kmh: float, roughness: float,
                    rng: np.random.Generator) -> np.ndarray:
    """Broadband road-induced vibration, amplitude scaling with speed."""
    amp = roughness * (0.004 + 0.00016 * speed_kmh)
    v = rng.normal(0.0, amp, size=(n, 3))
    # Low-pass: suspension attenuates above ~15 Hz.
    k = np.array([0.25, 0.5, 0.25])
    for c in range(3):
        v[:, c] = np.convolve(v[:, c], k, mode="same")
    v[:, 2] *= 1.6                      # vertical axis dominates
    return v


# --------------------------------------------------------------------- GPS
# All traces are built from ONE common driving base, then modified by the
# event. An earlier version gave crashes white noise around a constant while
# negatives got a random walk, so the PRE-IMPACT texture alone identified the
# class before the impact even happened. Shared base, divergent event.

def _gps_base(v0: float, rng) -> np.ndarray:
    """Ordinary speed texture: random-walk drift plus GPS measurement noise."""
    v = v0 + np.cumsum(rng.normal(0, 0.55, GPS_LEN))
    if rng.random() < 0.30:                              # gentle accel/decel
        v = v + np.linspace(0, rng.uniform(-12, 12), GPS_LEN)
    return v + rng.normal(0, 0.7, GPS_LEN)


def _gps_crash(v0: float, dv: float, rng) -> np.ndarray:
    """Speed collapsing at impact -- the delta-V the saturated IMU cannot see."""
    v = _gps_base(v0, rng)
    v_after = max(0.0, v[GPS_IMPACT_IDX] - dv)
    v[GPS_IMPACT_IDX] = v[GPS_IMPACT_IDX] * 0.45 + v_after * 0.55
    tail = GPS_LEN - GPS_IMPACT_IDX - 1
    if tail > 0:
        # Post-impact: coast down if still rolling, plus the same noise texture.
        decay = np.linspace(1.0, rng.uniform(0.45, 0.95), tail) if v_after > 1.0 else np.ones(tail)
        v[GPS_IMPACT_IDX + 1:] = v_after * decay + rng.normal(0, 0.7, tail)
    return np.clip(v, 0, None)


def _gps_brake(v0: float, dv: float, dur_s: float, rng) -> np.ndarray:
    """Deceleration ramp anchored at the trigger -- must NOT read as a crash."""
    v = _gps_base(v0, rng)
    k = max(2, int(round(dur_s)))
    st = GPS_IMPACT_IDX
    end = min(GPS_LEN, st + k)
    target = max(0.0, v[st] - dv)
    v[st:end] = np.linspace(v[st], target, end - st)
    if end < GPS_LEN:
        v[end:] = target + rng.normal(0, 0.7, GPS_LEN - end)
    return np.clip(v, 0, None)


def _gps_steady(v0: float, rng) -> np.ndarray:
    """Driving through a non-crash event, including any reaction braking."""
    v = _gps_base(v0, rng)
    if rng.random() < 0.55 and v0 > 12:
        k = int(rng.integers(2, 7))
        drop = float(rng.uniform(5, min(0.85 * v0, 60)))
        st = int(np.clip(GPS_IMPACT_IDX + rng.integers(-1, 3), 0, GPS_LEN - k))
        target = max(0.0, v[st] - drop)
        v[st:st + k] = np.linspace(v[st], target, k)
        v[st + k:] = target + rng.normal(0, 0.7, GPS_LEN - st - k)
    return np.clip(v, 0, None)


# --------------------------------------------------------------------- events
def make_event(kind: str, rng: np.random.Generator) -> dict:
    """Return ideal (pre-device) IMU, a GPS speed trace, and audio directives."""
    acc = np.zeros((WIN_LEN, 3))
    gyr = np.zeros((WIN_LEN, 3))
    R = _rot(rng)
    meta: dict = {"kind": kind, "dv_kmh": 0.0, "severity": 0}

    if kind == "CRASH":
        v0 = float(rng.uniform(25, 105))
        dv = float(rng.uniform(8, min(80, v0)))
        dur = float(rng.uniform(40, 200))                # ms, real crash pulses
        shape = rng.choice(["haversine", "halfsine", "square"], p=[0.5, 0.3, 0.2])
        n_tail = WIN_LEN - IMPACT_IDX
        pulse = crash_pulse(dv, dur, n_tail, IMU_HZ, shape)

        # Principal impact direction, plus off-axis coupling.
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        d[2] *= 0.45                                     # mostly horizontal
        acc[IMPACT_IDX:, :] += pulse[:, None] * d[None, :]

        # Structural ring-down of the body shell.
        for f0, z, a in [(18, 0.12, 0.9), (42, 0.2, 0.5), (95, 0.3, 0.25)]:
            rd = ringdown(n_tail, IMU_HZ, f0 * rng.uniform(0.8, 1.2), z,
                          a * dv / 40.0, rng)
            acc[IMPACT_IDX:, rng.integers(0, 3)] += rd

        # Rotation: spin-out or rollover.
        rollover = rng.random() < 0.14
        rate = rng.uniform(220, 620) if rollover else rng.uniform(25, 190)
        # A textbook exponential decay is far smoother than any real vehicle
        # rotation, and smoothness alone separated crashes from negatives
        # (tail-jitter AUC 0.80). Real spin-out is buffeted by tyre scrub,
        # secondary contacts and suspension response.
        prof = np.exp(-np.linspace(0, rng.uniform(2.5, 5.0), n_tail)) * rate
        prof = prof * (1.0 + rng.normal(0, 0.22, n_tail))
        prof += rng.normal(0, rate * 0.05, n_tail)
        ax = rng.integers(0, 3)
        gyr[IMPACT_IDX:, ax] += prof * rng.choice([-1, 1])
        for other in range(3):                       # off-axis coupling
            if other != ax:
                gyr[IMPACT_IDX:, other] += prof * rng.uniform(-0.35, 0.35)
        meta.update(dv_kmh=dv, severity=severity_from_dv(dv), rollover=rollover,
                    v0=v0, pulse_ms=dur)
        gps = _gps_crash(v0, dv, rng)
        # Audio gain drawn from a range that OVERLAPS the confusers. Previously
        # crashes were mixed ~4x louder than every negative, which made
        # aud_peak_db a 0.99-AUC feature on level alone. Level is not the
        # discriminator in reality -- spectral character is.
        audio = {"type": "crash", "gain": float(np.clip(rng.uniform(0.25, 1.3)
                                                        * (0.6 + dv / 90.0), 0.2, 1.4))}

    elif kind == "EMERGENCY_STOP":
        # Panic stop, frequently ending with a kerb/verge strike. The GPS
        # signature is a crash-sized delta-V; only its SHAPE (a ramp over
        # several samples rather than a single-sample collapse), the absence of
        # a crash acoustic signature, and the sub-rail IMU distinguish it.
        v0 = float(rng.uniform(45, 105))
        g_peak = float(rng.uniform(0.7, 1.1))
        dur_s = float(rng.uniform(1.8, 3.5))
        k = int(dur_s * IMU_HZ)
        t = (np.arange(k) + 0.5) / k
        prof = g_peak * np.sin(np.pi * t) ** 0.45
        end = min(WIN_LEN, IMPACT_IDX + k)
        acc[IMPACT_IDX:end, 0] -= prof[: end - IMPACT_IDX]
        acc[IMPACT_IDX:end, 2] += prof[: end - IMPACT_IDX] * 0.3
        if rng.random() < 0.55:                          # kerb / verge strike
            at = IMPACT_IDX + int(rng.uniform(0.6, 1.6) * IMU_HZ)
            kk = max(2, int(rng.uniform(0.02, 0.05) * IMU_HZ))
            if at + kk < WIN_LEN:
                pk = rng.uniform(4, 14)
                acc[at:at + kk, 2] += _halfsine(kk, pk)
                gyr[at:at + kk, rng.integers(0, 3)] += rng.uniform(60, 260)
                rem = WIN_LEN - (at + kk)
                if rem > 4:
                    acc[at + kk:, 2] += ringdown(rem, IMU_HZ,
                                                 rng.uniform(9, 15), 0.16, pk * 0.4, rng)
        # Nose-dive pitch throughout the stop, and yaw if the car steps out.
        pitch = g_peak * rng.uniform(8, 22) * np.sin(np.pi * t) ** 0.5
        gyr[IMPACT_IDX:end, 1] += pitch[: end - IMPACT_IDX] * (1 + rng.normal(0, .18, end - IMPACT_IDX))
        if rng.random() < 0.4:
            yr = WIN_LEN - IMPACT_IDX
            gyr[IMPACT_IDX:, 2] += (np.exp(-np.linspace(0, 3, yr)) * rng.uniform(30, 160)
                                    * (1 + rng.normal(0, .3, yr)))
        dv = float(min(v0, v0 * rng.uniform(0.75, 1.0)))
        gps = _gps_brake(v0, dv, dur_s, rng)
        meta.update(v0=v0, dv_kmh=dv)
        audio = {"type": "brake", "gain": float(rng.uniform(0.7, 1.3))}

    elif kind == "HARD_BRAKE":
        v0 = float(rng.uniform(30, 100))
        g_peak = float(rng.uniform(0.45, 0.95))          # tyre-limited
        dur_s = float(rng.uniform(1.5, 4.0))
        k = int(dur_s * IMU_HZ)
        t = (np.arange(k) + 0.5) / k
        prof = g_peak * np.sin(np.pi * t) ** 0.6         # smooth, no rail
        end = min(WIN_LEN, IMPACT_IDX + k)
        acc[IMPACT_IDX:end, 0] -= prof[: end - IMPACT_IDX]
        acc[IMPACT_IDX:end, 2] += prof[: end - IMPACT_IDX] * 0.22   # nose dive
        dv = min(v0, g_peak * 9.81 * dur_s * 0.6 * 3.6)
        gps = _gps_brake(v0, dv, dur_s, rng)
        meta.update(v0=v0, dv_kmh=dv)
        audio = {"type": "brake", "gain": float(g_peak)}

    elif kind in ("POTHOLE", "SPEED_BUMP"):
        v0 = float(rng.uniform(15, 80))
        n_hits = 1 if kind == "POTHOLE" else 2
        peak = rng.uniform(3.0, 12.0) if kind == "POTHOLE" else rng.uniform(2.0, 6.0)
        for h in range(n_hits):
            at = IMPACT_IDX + h * int(rng.uniform(0.25, 0.5) * IMU_HZ)
            k = max(2, int(rng.uniform(0.03, 0.07) * IMU_HZ))
            if at + k >= WIN_LEN:
                break
            p = _halfsine(k, peak)
            acc[at:at + k, 2] += p                       # vertical dominant
            acc[at:at + k, 0] += p * rng.uniform(-0.25, 0.25)
            gyr[at:at + k, rng.integers(0, 3)] += p * rng.uniform(4, 14)
            # Suspension response. A pothole strike does not simply stop: the
            # wheel hops at ~12 Hz and the body oscillates at ~1.5 Hz for a
            # second or more. Omitting this left negatives with zero
            # post-event energy and made ring-down a free crash cue.
            rem = WIN_LEN - (at + k)
            if rem > 4:
                for f0, zt, amp in ((12.0, 0.18, 0.35), (1.6, 0.10, 0.18)):
                    acc[at + k:, 2] += ringdown(rem, IMU_HZ,
                                                f0 * rng.uniform(0.8, 1.25),
                                                zt, peak * amp, rng)
                # Sustained body roll/pitch -- the rotational half of the same
                # suspension response. Without it only crashes had rotation
                # lasting more than a few samples.
                for axis in range(2):
                    gyr[at + k:, axis] += ringdown(
                        rem, IMU_HZ, rng.uniform(1.2, 2.6), rng.uniform(0.08, 0.16),
                        peak * rng.uniform(2.0, 7.0), rng)
        gps = _gps_steady(v0, rng)
        meta.update(v0=v0)
        audio = {"type": "thump", "gain": float(peak / 8.0)}

    elif kind == "PHONE_DROP":
        # Deliberately overlaps the crash's IMU signature: high peak, clipping,
        # multi-axis. Only GPS (~0 speed) and audio (a clatter, not a crash)
        # separate them. This is the single most important negative class.
        # Passengers and drivers drop phones at speed constantly. The earlier
        # v0 in [0, 6] km/h was wrong, and it let both the speed gate and GPS
        # separate drops from crashes for free.
        v0 = float(rng.uniform(0, 95))
        peak = float(rng.uniform(8, 40))
        at = IMPACT_IDX + int(rng.uniform(-0.3, 0.3) * IMU_HZ)
        k = max(2, int(rng.uniform(0.01, 0.06) * IMU_HZ))    # short, but overlapping
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        acc[at:at + k, :] += _halfsine(k, peak)[:, None] * d[None, :]
        for b in range(rng.integers(1, 4)):                  # bounces
            ab = at + k + int(rng.uniform(0.04, 0.2) * IMU_HZ) * (b + 1)
            if ab + k < WIN_LEN:
                acc[ab:ab + k, :] += _halfsine(k, peak * 0.35 ** (b + 1))[:, None] * d[None, :]
        # A dropped phone tumbles, bounces and settles over ~1 s, rotating the
        # whole time -- not a single brief spike.
        rem = WIN_LEN - at
        tumble = np.exp(-np.linspace(0, rng.uniform(2.0, 4.5), rem)) * rng.uniform(180, 900)
        tumble = tumble * (1.0 + rng.normal(0, 0.35, rem))
        for axis in range(3):
            gyr[at:, axis] += tumble * rng.uniform(-1.0, 1.0)
        gps = _gps_steady(v0, rng)
        meta.update(v0=v0)
        audio = {"type": "clatter", "gain": float(np.clip(peak / 30.0, 0.2, 1.0))}

    elif kind == "DOOR_SLAM":
        v0 = 0.0
        peak = float(rng.uniform(2, 6))
        at = IMPACT_IDX + int(rng.uniform(-0.2, 0.2) * IMU_HZ)
        k = max(2, int(0.05 * IMU_HZ))
        acc[at:at + k, rng.integers(0, 3)] += _halfsine(k, peak)
        gps = _gps_steady(v0, rng)
        audio = {"type": "slam", "gain": 0.8}

    elif kind == "ROUGH_ROAD":
        v0 = float(rng.uniform(20, 70))
        acc += _road_vibration(WIN_LEN, v0, rng.uniform(3.0, 8.0), rng)
        gps = _gps_steady(v0, rng)
        meta.update(v0=v0)
        audio = {"type": "rough", "gain": 0.6}

    else:  # NORMAL_DRIVE
        v0 = float(rng.uniform(0, 95))
        gps = _gps_steady(v0, rng)
        meta.update(v0=v0)
        audio = {"type": "none", "gain": 0.0}

    # Rotate into the phone's (unknown) mounting frame.
    acc = acc @ R.T
    gyr = gyr @ R.T

    meta["v0"] = meta.get("v0", 0.0)
    meta["label"] = int(kind in POSITIVE)
    return {"accel": acc, "gyro": gyr, "gps": gps, "audio": audio, "meta": meta}


# --------------------------------------------------------------------- audio
class AudioMixer:
    """Composes the acoustic channel from real recordings."""

    def __init__(self, crash_clips, esc_clips, esc_cats, rng,
                 crash_idx=None, esc_idx=None):
        """`crash_idx` / `esc_idx` restrict this mixer to a disjoint subset of
        source recordings.

        Without that restriction the same 46 crash waveforms appear in train
        and test, and the audio CNN simply memorises them -- which is how an
        audio-only baseline reached PR-AUC 1.000. Splitting by SOURCE CLIP is
        the only honest protocol when the positive corpus is 38 unique videos.
        """
        from ml.crash_detection.audio_data import CABIN_BG, IMPULSIVE_NEG, peak_index
        self.rng = rng
        if crash_idx is not None:
            crash_clips = [crash_clips[i] for i in crash_idx]
        if esc_idx is not None:
            esc_clips = [esc_clips[i] for i in esc_idx]
            esc_cats = [esc_cats[i] for i in esc_idx]
        self.crash = crash_clips
        # Impact onsets depend only on the clip, so locate them once per clip
        # rather than re-scanning a 36 s waveform on every generated sample.
        self.crash_peak = [peak_index(c) for c in crash_clips]
        by = {}
        for c, k in zip(esc_clips, esc_cats):
            by.setdefault(k, []).append(c)
        self.by = by
        self.bg = [c for k in CABIN_BG for c in by.get(k, [])]
        self.imp = [c for k in IMPULSIVE_NEG for c in by.get(k, [])]
        self.glass = by.get("glass_breaking", [])
        self.engine = by.get("engine", []) + by.get("train", [])

    def _slice(self, pool, n=AUDIO_LEN):
        if not pool:
            return np.zeros(n, dtype=np.float32)
        y = pool[self.rng.integers(len(pool))]
        if len(y) <= n:
            out = np.zeros(n, dtype=np.float32)
            out[: len(y)] = y
            return out
        s = self.rng.integers(0, len(y) - n)
        return y[s: s + n].copy()

    def background(self, speed_kmh: float) -> np.ndarray:
        """Cabin noise floor: engine/road, louder with speed."""
        b = self._slice(self.engine if self.engine else self.bg)
        lvl = 0.006 + 0.00035 * speed_kmh
        b = b / (np.abs(b).max() + 1e-9) * lvl
        return b + self.rng.normal(0, 0.0015, AUDIO_LEN).astype(np.float32)

    def event(self, spec: dict, speed_kmh: float) -> np.ndarray:
        from ml.crash_detection.audio_data import take_window
        y = self.background(speed_kmh)
        t, gain = spec["type"], spec["gain"]
        if t == "none" or gain <= 0:
            return y

        if t == "crash":
            ci = int(self.rng.integers(len(self.crash)))
            c = self.crash[ci]
            seg = take_window(c, self.crash_peak[ci], AUDIO_LEN, pre_frac=0.5)
            seg = seg / (np.abs(seg).max() + 1e-9) * gain * 0.22
            y = y + seg
            if self.glass and self.rng.random() < 0.55:
                g = self._slice(self.glass)
                g = g / (np.abs(g).max() + 1e-9) * gain * 0.2
                y = y + np.roll(g, AUDIO_LEN // 2)
        else:
            pool = {"brake": self.by.get("siren", []) + self.by.get("car_horn", []),
                    "thump": self.imp, "clatter": self.imp,
                    "slam": self.by.get("door_wood_knock", []) or self.imp,
                    "rough": self.bg}.get(t, self.imp)
            seg = self._slice(pool)
            # Amplitudes overlap the crash range on purpose. A pothole strike
            # or a dropped phone against a phone mic 30 cm away is genuinely
            # loud; separating classes by level alone was a mixing artifact.
            amp = {"brake": 0.20, "thump": 0.26, "clatter": 0.22,
                   "slam": 0.30, "rough": 0.10}.get(t, 0.20)
            seg = seg / (np.abs(seg).max() + 1e-9) * gain * amp
            y = y + np.roll(seg, AUDIO_LEN // 2)

        return np.clip(y, -1.0, 1.0).astype(np.float32)   # mic clips too
