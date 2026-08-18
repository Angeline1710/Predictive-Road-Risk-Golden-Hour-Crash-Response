package com.rrx.app.crash

import androidx.compose.runtime.Composable

/** Switches between UX-APPFLOW.md §15-17's screens based on
 * [CrashCountdownViewModel]'s state -- see [CrashFlowState] for why this
 * is one state machine rather than separate navigation destinations. */
@Composable
fun CrashFlowHost(state: CrashFlowState, onCancelRequested: () -> Unit) {
    when (state) {
        is CrashFlowState.Countdown -> CrashCountdownScreen(state.ui, onCancelRequested)
        is CrashFlowState.Cancelled -> CancelledScreen()
        is CrashFlowState.Sending, is CrashFlowState.Sent -> SendingScreen(state)
    }
}
