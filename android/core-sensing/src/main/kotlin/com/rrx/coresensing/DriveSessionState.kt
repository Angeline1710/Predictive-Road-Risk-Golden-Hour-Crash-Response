package com.rrx.coresensing

/** What [DriveSensingService] is doing right now, published for the UI. */
sealed interface DriveSessionState {
    data object Idle : DriveSessionState

    /** Sensors are live but the 200-sample IMU window hasn't filled yet
     * (first ~4 s after starting). */
    data object WarmingUp : DriveSessionState

    data class Sensing(
        val peakAccelG: Float,
        val speedKmh: Float?,
        val stageA: StageAResult,
    ) : DriveSessionState

    /** The device is missing a required sensor (rare, but real on very
     * cheap hardware -- ImuSensorSource.available is what detects this). */
    data class Unavailable(val reason: String) : DriveSessionState
}
