package com.rrx.app.crash

import com.rrx.coredetection.IncidentSeverity
import com.rrx.coretransport.TransportResult

/** Everything [CrashCountdownViewModel] needs to build a real alert
 * payload, captured at the moment Stage-A fired -- not re-derived when
 * the countdown ends, since the sensor state at trigger time is what the
 * alert should describe. */
data class CrashTriggerParams(
    val alertUuid: String,
    val occurredAtIso: String,
    val severity: IncidentSeverity,
    val pCrash: Float,
    val peakAccelG: Float,
    val lat: Double,
    val lon: Double,
    val accuracyM: Float,
    val headingDeg: Float,
    val speedKmh: Float,
)

data class CountdownUiState(
    val secondsRemaining: Int,
    val totalSeconds: Int,
    val severity: IncidentSeverity,
    val buttonEnabled: Boolean,
)

/** UX-APPFLOW.md §15-17's screen sequence, as one state machine rather
 * than separate navigation destinations -- there's no navigation library
 * in this scaffold, and the whole flow is meant to feel like one
 * continuous, uninterruptible moment anyway. */
sealed interface CrashFlowState {
    data class Countdown(val ui: CountdownUiState) : CrashFlowState
    data object Cancelled : CrashFlowState
    data object Sending : CrashFlowState
    data class Sent(val result: TransportResult) : CrashFlowState
}
