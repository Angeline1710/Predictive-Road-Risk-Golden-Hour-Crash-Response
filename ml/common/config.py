"""Shared constants for the RRX model stack.

Everything that both models (or several stages of one model) need to agree on
lives here, so a change to the window length or the sample rate cannot silently
desynchronise the generator from the trainer.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[2]
ML = ROOT / "ml"
DATA_RAW = ML / "data" / "raw"
DATA_PROC = ML / "data" / "processed"
ARTIFACTS = ML / "artifacts"
REPORTS = ML / "reports"
for _p in (DATA_RAW, DATA_PROC, ARTIFACTS, REPORTS):
    _p.mkdir(parents=True, exist_ok=True)

# User-supplied reference data
DOWNLOADS = Path.home() / "Downloads"
TN_ACCIDENTS_CSV = DOWNLOADS / "tn_road_accident_dataset_original.csv"
INDIAN_ROADS_CSV = DOWNLOADS / "indian_roads_dataset.csv"

# ---------------------------------------------------------------- Model A: windows
IMU_HZ = 50                      # PRD 6.1.1 sampling rate
WIN_SEC = 4.0                    # PRD 7.1 input window
WIN_LEN = int(IMU_HZ * WIN_SEC)  # 200 samples
PRE_IMPACT_SEC = 2.0             # impact sits at the window midpoint
IMPACT_IDX = int(IMU_HZ * PRE_IMPACT_SEC)

AUDIO_HZ = 16_000                # mic downsampled on-device
AUDIO_LEN = int(AUDIO_HZ * WIN_SEC)
N_MELS = 64
HOP = 512                        # -> 126 frames over 4 s

GPS_HZ = 1                       # FusedLocationProvider while moving (PRD 6.1.1)
GPS_SEC = 12.0                   # 8 s pre / 4 s post
GPS_LEN = int(GPS_HZ * GPS_SEC)
GPS_IMPACT_IDX = 8

# ---------------------------------------------------------------- device physics
# Consumer smartphone IMUs are low-g parts. This is the entire reason the
# multi-modal design exists: a real crash drives the accelerometer past its rail,
# so peak magnitude is NOT observable and the clipping pattern must carry the signal.
#
# Representative full-scale ranges across the Indian budget/mid Android install base.
# LSM6DS*/BMI160/ICM-4xxxx families are typically configured to +/-8 g or +/-16 g by
# the OEM's sensor HAL; very few phones expose +/-32 g.
ACCEL_RAILS_G = (8.0, 16.0, 16.0, 16.0, 32.0)   # sampled per synthetic device
GYRO_RAIL_DPS = 2000.0                           # deg/s, near-universal max FS
ACCEL_NOISE_G = 0.012                            # ~12 mg RMS, typical MEMS noise density
GYRO_NOISE_DPS = 0.6

# Stage-A cheap gate (PRD 6.1.2). Note this is evaluated on CLIPPED data, exactly
# as it would be on-device.
STAGE_A_G = 4.0
STAGE_A_MIN_SPEED_KMH = 20.0

# ---------------------------------------------------------------- labels
SEVERITY = ["MINOR", "MODERATE", "SEVERE", "CRITICAL"]
SEV_IDX = {s: i for i, s in enumerate(SEVERITY)}

# Delta-V bands (km/h) used to assign severity to a synthesised crash.
# Grounded in the standard injury-risk relationship: risk of serious injury rises
# steeply above ~30 km/h delta-V for a belted occupant.
SEVERITY_DV_BANDS = [(8, 18), (18, 30), (30, 48), (48, 80)]

MODALITIES = ("imu", "audio", "gps")

SEED = 20260815
