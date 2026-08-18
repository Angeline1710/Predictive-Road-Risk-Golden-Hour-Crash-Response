package com.rrx.app.ui.drive

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.app.crash.CrashTriggerNotifier
import com.rrx.coredetection.CrashClassifier
import com.rrx.coredetection.CrashPrediction
import com.rrx.coredetection.TabularFeatures
import com.rrx.coresensing.DriveSensingBus
import com.rrx.coresensing.DriveSensingService
import com.rrx.coresensing.DriveSessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.stateIn
import java.util.concurrent.atomic.AtomicBoolean
import javax.inject.Inject

/**
 * Thin wrapper over [DriveSensingBus] and [DriveSensingService]'s
 * start/stop lifecycle, plus the glue core-sensing and core-detection
 * don't have themselves: on the rising edge of Stage-A's degraded arm
 * (see [com.rrx.coresensing.StageAGate]), extracts tabular features and
 * runs [CrashClassifier] once, off the main thread. Edge-triggered, not
 * level-triggered -- classification is real inference work, not something
 * to re-run every 200ms evaluation tick while a gate stays open.
 */
@HiltViewModel
class DriveViewModel @Inject constructor(
    private val application: Application,
) : AndroidViewModel(application) {

    private val classifierLazy = lazy { CrashClassifier(application) }
    private var wasStageATriggered = false

    // TFLite's Interpreter is documented as not safe for concurrent
    // invocation on the same instance. A single rising edge can only ever
    // launch one classify() coroutine, but a real crash can plausibly
    // produce a second rising edge (a secondary impact) before the first
    // classification finishes; without this guard that would be two
    // concurrent calls into the same Interpreter.
    private val isClassifying = AtomicBoolean(false)

    private val _prediction = MutableStateFlow<CrashPrediction?>(null)
    val prediction: StateFlow<CrashPrediction?> = _prediction.asStateFlow()

    val sessionState: StateFlow<DriveSessionState> = DriveSensingBus.state
        .onEach(::maybeClassify)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), DriveSessionState.Idle)

    private fun maybeClassify(state: DriveSessionState) {
        if (state !is DriveSessionState.Sensing) {
            wasStageATriggered = false
            return
        }
        val triggered = state.stageA.degraded
        val gpsWindow = state.gpsWindow
        if (triggered && !wasStageATriggered && gpsWindow != null && isClassifying.compareAndSet(false, true)) {
            viewModelScope.launch(Dispatchers.Default) {
                try {
                    val tab = TabularFeatures.extract(state.imuWindow, state.accelRailG, gpsWindow)
                    val prediction = classifierLazy.value.classify(state.imuWindow, gpsWindow, tab)
                    _prediction.value = prediction
                    CrashTriggerNotifier.maybeTrigger(application, state, prediction)
                } finally {
                    isClassifying.set(false)
                }
            }
        }
        wasStageATriggered = triggered
    }

    fun startSensing() = DriveSensingService.start(application)

    fun stopSensing() = DriveSensingService.stop(application)

    override fun onCleared() {
        // classify() has no suspension points, so cancelling viewModelScope
        // does not interrupt an in-flight native call -- closing the
        // interpreter out from under it would be a use-after-close in the
        // native layer. Skipping close() here leaks the interpreter in
        // that narrow window (ViewModel cleared mid-inference) rather than
        // risk that; a real fix needs the close to wait on isClassifying,
        // which is more synchronization than this scaffold's one screen
        // warrants.
        if (classifierLazy.isInitialized() && !isClassifying.get()) {
            classifierLazy.value.close()
        }
        super.onCleared()
    }
}
