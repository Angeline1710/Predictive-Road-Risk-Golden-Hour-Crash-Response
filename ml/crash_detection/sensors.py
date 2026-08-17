"""Device physics: what a real phone actually records during a crash.

The central fact this module encodes:

    A consumer Android accelerometer saturates at +/-8..16 g.
    A 40 km/h delta-V barrier impact produces 20-60 g at a loose object in
    the cabin. So the sensor CLIPS, and peak acceleration is unmeasurable.

Apple's answer was hardware -- the iPhone 14 added a dedicated 256 g
accelerometer specifically for Crash Detection. We cannot add hardware, so we
extract signal from the shape of the clipping instead: how long the rail is
held, how many axes rail simultaneously, and how the signal recovers.

Everything downstream of `apply_device_response` sees only what the phone
would actually have seen.
"""
from __future__ import annotations

import numpy as np

from ml.common.config import (
    ACCEL_NOISE_G,
    ACCEL_RAILS_G,
    GYRO_NOISE_DPS,
    GYRO_RAIL_DPS,
    IMU_HZ,
)


def sample_device(rng: np.random.Generator) -> dict:
    """Draw a plausible handset sensor configuration."""
    return {
        "accel_rail_g": float(rng.choice(ACCEL_RAILS_G)),
        "gyro_rail_dps": GYRO_RAIL_DPS,
        "accel_noise_g": float(ACCEL_NOISE_G * rng.uniform(0.6, 1.8)),
        "gyro_noise_dps": float(GYRO_NOISE_DPS * rng.uniform(0.6, 1.8)),
        # Cheap MEMS parts have a small persistent zero-g offset.
        "accel_bias_g": rng.normal(0.0, 0.02, size=3),
        # Real Android sensor delivery jitters around the nominal rate.
        "rate_jitter": float(rng.uniform(0.0, 0.06)),
    }


def apply_device_response(
    accel_g: np.ndarray,
    gyro_dps: np.ndarray,
    device: dict,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Push an ideal signal through a real sensor.

    Args:
        accel_g:  (T, 3) true linear acceleration in g
        gyro_dps: (T, 3) true angular rate in deg/s
        device:   from `sample_device`

    Returns:
        accel_obs: (T, 3) clipped, biased, noisy acceleration in g
        gyro_obs:  (T, 3) clipped, noisy angular rate in deg/s
        clip_mask: (T, 3) 1.0 where the accelerometer was on its rail
    """
    rail = device["accel_rail_g"]

    a = accel_g + device["accel_bias_g"][None, :]
    a = a + rng.normal(0.0, device["accel_noise_g"], size=a.shape)

    # The rail is a hard limit, not a soft compression.
    clip_mask = (np.abs(a) >= rail).astype(np.float32)
    a = np.clip(a, -rail, rail)

    g = gyro_dps + rng.normal(0.0, device["gyro_noise_dps"], size=gyro_dps.shape)
    g = np.clip(g, -device["gyro_rail_dps"], device["gyro_rail_dps"])

    return a.astype(np.float32), g.astype(np.float32), clip_mask


def saturation_features(accel_obs: np.ndarray, clip_mask: np.ndarray, rail_g: float) -> dict:
    """Scalar descriptors of the clipping event.

    These are the features that replace 'peak g' once peak g is unobservable.
    A phone drop rails briefly on one axis; a crash rails longer, on several
    axes at once, and takes longer to come off the rail.
    """
    n_clipped = float(clip_mask.sum())
    per_axis = clip_mask.sum(axis=0)                       # (3,)
    axes_clipped = float((per_axis > 0).sum())
    simultaneous = float((clip_mask.sum(axis=1) >= 2).sum())

    # Longest unbroken run of "any axis on the rail" -> impact duration proxy.
    any_clip = (clip_mask.max(axis=1) > 0).astype(np.int8)
    # Vectorised run-length: cumulative count minus its value at the last zero.
    if any_clip.any():
        idx = np.arange(len(any_clip))
        csum = np.cumsum(any_clip)
        reset = np.maximum.accumulate(np.where(any_clip == 0, csum, 0))
        longest = int((csum - reset).max())
    else:
        longest = 0

    mag = np.linalg.norm(accel_obs, axis=1)
    # Impulse is still measurable even when peak is not -- the integral of the
    # clipped signal is a lower bound on true delta-V, and a useful one.
    impulse = float(mag.sum() / IMU_HZ)

    # How fast the signal climbed into the rail (g per sample).
    onset = 0.0
    if n_clipped > 0:
        first = int(np.argmax(any_clip))
        lo = max(0, first - 5)
        if first > lo:
            onset = float((mag[first] - mag[lo]) / (first - lo))

    return {
        "sat_n_clipped": n_clipped,
        "sat_frac_clipped": n_clipped / clip_mask.size,
        "sat_axes_clipped": axes_clipped,
        "sat_simultaneous": simultaneous,
        "sat_longest_run": float(longest),
        "sat_longest_run_ms": float(longest / IMU_HZ * 1000.0),
        "sat_onset_slope": onset,
        "sat_rail_g": float(rail_g),
        "imu_impulse": impulse,
        "imu_peak_obs_g": float(mag.max()),
        "imu_rms_g": float(np.sqrt((mag ** 2).mean())),
    }


def crash_pulse(
    delta_v_kmh: float,
    duration_ms: float,
    n: int,
    hz: int = IMU_HZ,
    shape: str = "haversine",
) -> np.ndarray:
    """A vehicle crash acceleration pulse, in g, length `n`, impact at index 0.

    Uses the haversine crash pulse standard in vehicle safety analysis. The
    pulse is scaled so that its integral equals the requested delta-V, which is
    what makes the severity label physically meaningful rather than arbitrary.
    """
    dv_ms = delta_v_kmh / 3.6
    dur_s = duration_ms / 1000.0
    k = max(2, int(round(dur_s * hz)))

    t = np.linspace(0.0, 1.0, k, endpoint=False)
    if shape == "haversine":
        p = 0.5 * (1.0 - np.cos(2.0 * np.pi * t))
    elif shape == "halfsine":
        p = np.sin(np.pi * t)
    else:  # "square-ish", stiff barrier impact
        p = np.ones_like(t)
        p[: max(1, k // 8)] = np.linspace(0, 1, max(1, k // 8))
        p[-max(1, k // 8):] = np.linspace(1, 0, max(1, k // 8))

    area = p.sum() / hz                       # m/s per unit amplitude
    amp_ms2 = dv_ms / max(area, 1e-9)
    pulse = p * amp_ms2 / 9.81                # -> g

    out = np.zeros(n, dtype=np.float64)
    out[:k] = pulse[: min(k, n)]
    return out


def ringdown(n: int, hz: int, f0: float, zeta: float, amp: float, rng) -> np.ndarray:
    """Structural ring-down after impact: damped oscillation of the body shell."""
    t = np.arange(n) / hz
    phase = rng.uniform(0, 2 * np.pi)
    return amp * np.exp(-zeta * 2 * np.pi * f0 * t) * np.sin(2 * np.pi * f0 * t + phase)
