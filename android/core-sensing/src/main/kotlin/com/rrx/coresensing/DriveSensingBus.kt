package com.rrx.coresensing

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * In-process publish point between [DriveSensingService] and the UI layer.
 * A bound service (Messenger/AIDL) would be the more "correct" Android
 * pattern for cross-process communication, but everything here runs in a
 * single process, so a process-wide StateFlow is simpler and just as
 * correct for this scaffold -- documented as a deliberate simplification,
 * not an oversight, in case core-transport later needs cross-process
 * access (e.g. a separate :sensing process for isolation).
 */
object DriveSensingBus {
    private val _state = MutableStateFlow<DriveSessionState>(DriveSessionState.Idle)
    val state: StateFlow<DriveSessionState> = _state.asStateFlow()

    internal fun publish(newState: DriveSessionState) {
        _state.value = newState
    }
}
