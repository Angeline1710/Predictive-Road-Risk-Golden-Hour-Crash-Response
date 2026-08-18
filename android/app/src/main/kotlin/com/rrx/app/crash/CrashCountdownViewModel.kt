package com.rrx.app.crash

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.coredetection.IncidentSeverity
import com.rrx.coretransport.AlertTransport
import com.rrx.coretransport.dto.AlertCreateDto
import com.rrx.coretransport.dto.DetectionDto
import com.rrx.coretransport.dto.LocationDto
import com.rrx.coretransport.dto.MotionDto
import com.rrx.coretransport.dto.WindowDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * UX-APPFLOW.md §15's cancel-window state machine: countdown -> (cancel |
 * expire -> send -> sent). "The most important screen in the product" --
 * see that section for the full reasoning behind each timing/behaviour
 * choice mirrored here.
 */
@HiltViewModel
class CrashCountdownViewModel @Inject constructor(
    application: Application,
    private val alertTransport: AlertTransport,
) : AndroidViewModel(application) {

    private val audio = CrashAudioController(application)
    private val haptic = CrashHapticController(application)

    private var initialized = false
    private var params: CrashTriggerParams? = null

    private val _state = MutableStateFlow<CrashFlowState>(
        CrashFlowState.Countdown(CountdownUiState(0, 0, IncidentSeverity.MINOR, buttonEnabled = false))
    )
    val state: StateFlow<CrashFlowState> = _state.asStateFlow()

    /** Idempotent -- the hosting Activity calls this from `onCreate()`,
     * which can re-run on configuration change; the countdown must not
     * restart from a config change (a screen rotation is not a reason to
     * give someone their ten seconds back). */
    fun start(trigger: CrashTriggerParams) {
        if (initialized) return
        initialized = true
        params = trigger

        val total = totalSecondsFor(trigger.severity)
        _state.value = CrashFlowState.Countdown(CountdownUiState(total, total, trigger.severity, buttonEnabled = false))

        audio.start()
        haptic.start()

        viewModelScope.launch {
            delay(BUTTON_ENABLE_DELAY_MS)
            updateCountdown { it.copy(buttonEnabled = true) }
        }

        viewModelScope.launch {
            for (remaining in total downTo 0) {
                if (_state.value !is CrashFlowState.Countdown) return@launch // cancelled mid-countdown
                updateCountdown { it.copy(secondsRemaining = remaining) }
                audio.announceSecond(remaining)
                if (remaining == 0) break
                delay(1_000L)
            }
            if (_state.value is CrashFlowState.Countdown) onExpired()
        }
    }

    /** Button and volume-key cancel both call this. UX-APPFLOW.md §15.3
     * only specifies the 800ms guard for the button explicitly, but the
     * guard's own rationale -- an impact striking the phone shouldn't be
     * able to cancel the alert -- applies just as much to a volume key a
     * flying phone could physically strike, so both are gated the same
     * way here rather than trusting the spec's silence on volume keys as
     * permission to skip it. */
    fun cancel() {
        val current = _state.value
        if (current !is CrashFlowState.Countdown || !current.ui.buttonEnabled) return
        stopAlarms()
        _state.value = CrashFlowState.Cancelled
    }

    private fun onExpired() {
        stopAlarms()
        _state.value = CrashFlowState.Sending
        viewModelScope.launch {
            val trigger = params ?: return@launch
            val result = alertTransport.send(buildPayload(trigger))
            _state.value = CrashFlowState.Sent(result)
        }
    }

    private fun buildPayload(p: CrashTriggerParams): AlertCreateDto = AlertCreateDto(
        alertUuid = p.alertUuid,
        occurredAt = p.occurredAtIso,
        location = LocationDto(lat = p.lat, lon = p.lon, accuracyM = p.accuracyM.toDouble()),
        motion = MotionDto(
            speedKmh = p.speedKmh.toDouble(),
            headingDeg = p.headingDeg.toDouble(),
            peakG = p.peakAccelG.toDouble(),
            // rollover/stillMoving aren't derivable from what DriveSensingService
            // currently publishes -- real values need dedicated post-impact
            // sensor logic this pass doesn't build. Left at their honest
            // "unknown" defaults rather than guessed.
            rollover = false,
            stillMoving = null,
        ),
        detection = DetectionDto(
            pCrash = p.pCrash.toDouble(),
            severity = p.severity.name,
            modelVersion = "crash_fusion_deployable_v1",
        ),
        window = WindowDto(durationS = totalSecondsFor(p.severity), outcome = "EXPIRED"),
        // This is a real Stage-A trigger from real sensor data running
        // through the real classifier -- not a canned demo -- so
        // isSimulated is false here, unlike ui.transport.TransportSection's
        // test button.
        isSimulated = false,
    )

    private fun totalSecondsFor(severity: IncidentSeverity): Int =
        if (severity == IncidentSeverity.CRITICAL) CRITICAL_WINDOW_S else NORMAL_WINDOW_S

    private fun updateCountdown(transform: (CountdownUiState) -> CountdownUiState) {
        val current = _state.value
        if (current is CrashFlowState.Countdown) _state.value = CrashFlowState.Countdown(transform(current.ui))
    }

    private fun stopAlarms() {
        audio.stop()
        haptic.stop()
    }

    override fun onCleared() {
        stopAlarms()
        super.onCleared()
    }

    private companion object {
        const val BUTTON_ENABLE_DELAY_MS = 800L
        const val NORMAL_WINDOW_S = 10
        // UX-APPFLOW.md §15.4's full condition is "CRITICAL + no post-impact
        // motion + phone not picked up" -- this build only has severity to
        // go on (post-impact motion and pickup detection aren't wired),
        // so CRITICAL alone triggers the shorter window. Documented
        // simplification, not the full spec.
        const val CRITICAL_WINDOW_S = 5
    }
}
