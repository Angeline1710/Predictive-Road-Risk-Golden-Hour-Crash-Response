package com.rrx.app.ui.transport

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.coretransport.AlertTransport
import com.rrx.coretransport.TransportResult
import com.rrx.coretransport.dto.AlertCreateDto
import com.rrx.coretransport.dto.DetectionDto
import com.rrx.coretransport.dto.LocationDto
import com.rrx.coretransport.dto.MotionDto
import com.rrx.coretransport.dto.WindowDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.OffsetDateTime
import java.util.UUID
import javax.inject.Inject

sealed interface SendState {
    data object Idle : SendState
    data object Sending : SendState
    data class Done(val result: TransportResult) : SendState
}

/**
 * Exercises [AlertTransport] end to end against the real backend, the
 * same "one real screen proves the contract" pattern as
 * ui.home.HomeViewModel's device registration. `isSimulated = true` on
 * every payload this builds -- there is no cancel-window screen yet to
 * produce a real, user-confirmed crash payload, so this must never look
 * like it originated from an actual incident.
 */
@HiltViewModel
class TransportViewModel @Inject constructor(
    private val alertTransport: AlertTransport,
) : ViewModel() {

    private val _state = MutableStateFlow<SendState>(SendState.Idle)
    val state: StateFlow<SendState> = _state.asStateFlow()

    fun sendTestAlert() {
        _state.value = SendState.Sending
        viewModelScope.launch {
            val payload = AlertCreateDto(
                alertUuid = UUID.randomUUID().toString(),
                occurredAt = OffsetDateTime.now().toString(),
                location = LocationDto(lat = 12.86, lon = 80.15, accuracyM = 8.0),
                motion = MotionDto(speedKmh = 68.4, headingDeg = 142.0, peakG = 9.1, rollover = false, stillMoving = false),
                detection = DetectionDto(pCrash = 0.93, severity = "SEVERE", modelVersion = "crash_fusion_deployable_v1"),
                window = WindowDto(durationS = 10, outcome = "EXPIRED"),
                isSimulated = true,
            )
            _state.value = SendState.Done(alertTransport.send(payload))
        }
    }
}
