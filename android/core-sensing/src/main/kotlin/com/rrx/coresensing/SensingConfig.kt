package com.rrx.coresensing

/**
 * Transcribed verbatim from ml/common/config.py -- that file is the single
 * source of truth (it says so itself: "a change to the window length or the
 * sample rate cannot silently desynchronise the generator from the
 * trainer"). The same applies here: if this drifts from ml/common/config.py,
 * the on-device window no longer matches what crash_fusion_deployable_v1.tflite
 * was trained on.
 */
object SensingConfig {
    const val IMU_HZ = 50
    const val WIN_SEC = 4.0
    const val WIN_LEN = (IMU_HZ * WIN_SEC).toInt() // 200 samples

    const val GPS_HZ = 1
    const val GPS_SEC = 12.0
    const val GPS_LEN = (GPS_HZ * GPS_SEC).toInt() // 12 samples
    const val GPS_IMPACT_IDX = 8

    const val GYRO_RAIL_DPS = 2000.0f

    // Stage-A cheap gate (PRD §6.1.2), evaluated on clipped data exactly as
    // it would be on-device -- ml/crash_detection/build_dataset.py's
    // stage_a_pass() is the reference implementation StageAGate mirrors.
    const val STAGE_A_G = 4.0f
    const val STAGE_A_MIN_SPEED_KMH = 20.0f

    // How stale a location fix must be before Stage-A treats speed as
    // unknown rather than trusting a number from minutes ago -- GPS_HZ
    // implies a fresh fix roughly every second while moving.
    const val GPS_FIX_STALE_MS = 5_000L
}
