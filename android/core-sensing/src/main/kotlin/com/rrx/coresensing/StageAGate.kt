package com.rrx.coresensing

/**
 * Result of evaluating the Stage-A gate. `full` is what actually promotes
 * a window to the (not-yet-built) TFLite classifier under normal
 * conditions; `degraded` is the superset the model is trained on, and the
 * one that matters -- see [StageAGate.evaluate].
 */
data class StageAResult(val full: Boolean, val degraded: Boolean)

/**
 * PRD §6.1.2's cheap gate, evaluated on already-clipped data exactly as it
 * would run on-device -- mirrors ml/crash_detection/build_dataset.py's
 * `stage_a_pass()` line for line, including which arm is authoritative:
 *
 *   full:      |a| >= STAGE_A_G AND speed >= STAGE_A_MIN_SPEED_KMH.
 *              The speed precondition is what eliminates dropped phones.
 *   degraded:  |a| >= STAGE_A_G only. This is what actually runs whenever
 *              GPS is unavailable (tunnels, urban canyons, cold start,
 *              indoors) -- common on exactly the rural/highway stretches
 *              this product targets. Dropped phones DO reach the
 *              classifier here; audio becomes the only defence.
 *
 * The model is trained on the degraded (superset) gate, so `speedKmh ==
 * null` (no fix, or the last fix is older than GPS_FIX_STALE_MS) must
 * still evaluate `degraded` rather than silently doing nothing -- going
 * quiet exactly when GPS drops is the one failure mode this product
 * cannot afford.
 */
object StageAGate {
    fun evaluate(peakAccelMagnitudeG: Float, speedKmh: Float?): StageAResult {
        val degraded = peakAccelMagnitudeG >= SensingConfig.STAGE_A_G
        val full = degraded && speedKmh != null && speedKmh >= SensingConfig.STAGE_A_MIN_SPEED_KMH
        return StageAResult(full = full, degraded = degraded)
    }
}
