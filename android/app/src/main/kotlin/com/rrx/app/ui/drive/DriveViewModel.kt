package com.rrx.app.ui.drive

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.coresensing.DriveSensingBus
import com.rrx.coresensing.DriveSensingService
import com.rrx.coresensing.DriveSessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

/**
 * Thin wrapper over [DriveSensingBus] and [DriveSensingService]'s
 * start/stop lifecycle -- the actual sensing logic lives in core-sensing,
 * which this ViewModel has no business duplicating.
 */
@HiltViewModel
class DriveViewModel @Inject constructor(
    private val application: Application,
) : AndroidViewModel(application) {

    val sessionState: StateFlow<DriveSessionState> = DriveSensingBus.state.stateIn(
        viewModelScope, SharingStarted.WhileSubscribed(5_000), DriveSessionState.Idle,
    )

    fun startSensing() = DriveSensingService.start(application)

    fun stopSensing() = DriveSensingService.stop(application)
}
