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
        /** Raw (200,9) window backing [peakAccelG] and [stageA] -- exposed
         * so a higher layer (core-detection, via `app`) can run feature
         * extraction and classification without core-sensing needing to
         * know classification exists. Always present once this state is
         * reachable at all. */
        val imuWindow: Array<FloatArray>,
        /** Raw (12,) GPS speed window, matching [imuWindow]'s role --
         * unlike the IMU window (full after ~4s), this stays null for the
         * first ~8s after starting, since GpsSpeedBuffer needs a full 12s
         * of fixes. */
        val gpsWindow: FloatArray?,
        val accelRailG: Float,
        /** The latest full location fix -- null under the same conditions
         * as [gpsWindow]. A real alert payload needs lat/lon, which
         * [speedKmh] alone can't provide. */
        val gpsFix: GpsFix?,
    ) : DriveSessionState {
        override fun equals(other: Any?): Boolean =
            other is Sensing && peakAccelG == other.peakAccelG && speedKmh == other.speedKmh &&
                stageA == other.stageA && accelRailG == other.accelRailG && gpsFix == other.gpsFix &&
                imuWindow.contentDeepEquals(other.imuWindow) &&
                (gpsWindow?.contentEquals(other.gpsWindow ?: floatArrayOf()) ?: (other.gpsWindow == null))

        override fun hashCode(): Int {
            var result = peakAccelG.hashCode()
            result = 31 * result + (speedKmh?.hashCode() ?: 0)
            result = 31 * result + stageA.hashCode()
            result = 31 * result + imuWindow.contentDeepHashCode()
            result = 31 * result + (gpsWindow?.contentHashCode() ?: 0)
            result = 31 * result + accelRailG.hashCode()
            result = 31 * result + (gpsFix?.hashCode() ?: 0)
            return result
        }
    }

    /** The device is missing a required sensor (rare, but real on very
     * cheap hardware -- ImuSensorSource.available is what detects this). */
    data class Unavailable(val reason: String) : DriveSessionState
}
