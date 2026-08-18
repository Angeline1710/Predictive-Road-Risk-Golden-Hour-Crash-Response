package com.rrx.app.crash

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.KeyEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.rrx.app.ui.theme.RrxTheme
import com.rrx.coredetection.IncidentSeverity
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.delay

/**
 * Hosts UX-APPFLOW.md §15-17's whole crash flow. A dedicated Activity,
 * not a Composable route within MainActivity, because "Lock-screen
 * behaviour: zero friction" (§15.3) needs Activity-level window flags
 * (`setShowWhenLocked`/`setTurnScreenOn`) that only make sense at that
 * granularity -- and because this needs to launch from a background
 * foreground-service context, not just from user navigation inside an
 * already-open app.
 */
@AndroidEntryPoint
class CrashCountdownActivity : ComponentActivity() {

    private val viewModel: CrashCountdownViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // §15.3 "Lock-screen behaviour": show over the keyguard without
        // dismissing/unlocking it -- "No unlock, no PIN, no biometric."
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                    WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
            )
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        // "Screen brightness forced to maximum, overriding auto-brightness,
        // for the full 10s" (§15.3).
        window.attributes = window.attributes.apply { screenBrightness = 1.0f }

        // §15.3's "what is absent": "no back gesture... One decision, one
        // control." An always-enabled callback that does nothing is the
        // current, non-deprecated way to actually suppress back (the
        // predictive-back gesture preview included), not the old
        // `onBackPressed()` override.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() = Unit
        })

        readTriggerFromIntent()?.let(viewModel::start)

        setContent {
            RrxTheme {
                val state by viewModel.state.collectAsState()
                CrashFlowHost(state, onCancelRequested = viewModel::cancel)

                LaunchedEffect(state) {
                    if (state is CrashFlowState.Cancelled) {
                        delay(AUTO_RETURN_DELAY_MS) // §16: auto-returns after 8s
                        finish()
                    }
                }
            }
        }
    }

    /** §15.3: "Either volume key cancels. This is not a convenience -- it
     * is a hard requirement." Consuming the event (returning true) also
     * suppresses the normal system volume UI, which is correct here --
     * this screen has exactly one decision, and a volume toast fighting
     * for attention against it is exactly the kind of noise §15.3's "what
     * is absent" principle rules out. */
    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_VOLUME_UP || keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
            viewModel.cancel()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    private fun readTriggerFromIntent(): CrashTriggerParams? {
        val alertUuid = intent.getStringExtra(EXTRA_ALERT_UUID) ?: return null
        val severity = intent.getStringExtra(EXTRA_SEVERITY)?.let {
            runCatching { IncidentSeverity.valueOf(it) }.getOrNull()
        } ?: return null
        return CrashTriggerParams(
            alertUuid = alertUuid,
            occurredAtIso = intent.getStringExtra(EXTRA_OCCURRED_AT) ?: return null,
            severity = severity,
            pCrash = intent.getFloatExtra(EXTRA_P_CRASH, 0f),
            peakAccelG = intent.getFloatExtra(EXTRA_PEAK_ACCEL_G, 0f),
            lat = intent.getDoubleExtra(EXTRA_LAT, 0.0),
            lon = intent.getDoubleExtra(EXTRA_LON, 0.0),
            accuracyM = intent.getFloatExtra(EXTRA_ACCURACY_M, 0f),
            headingDeg = intent.getFloatExtra(EXTRA_HEADING_DEG, 0f),
            speedKmh = intent.getFloatExtra(EXTRA_SPEED_KMH, 0f),
        )
    }

    companion object {
        private const val AUTO_RETURN_DELAY_MS = 8_000L

        const val EXTRA_ALERT_UUID = "alert_uuid"
        const val EXTRA_OCCURRED_AT = "occurred_at"
        const val EXTRA_SEVERITY = "severity"
        const val EXTRA_P_CRASH = "p_crash"
        const val EXTRA_PEAK_ACCEL_G = "peak_accel_g"
        const val EXTRA_LAT = "lat"
        const val EXTRA_LON = "lon"
        const val EXTRA_ACCURACY_M = "accuracy_m"
        const val EXTRA_HEADING_DEG = "heading_deg"
        const val EXTRA_SPEED_KMH = "speed_kmh"

        fun intentFor(context: android.content.Context, params: CrashTriggerParams): Intent =
            Intent(context, CrashCountdownActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                putExtra(EXTRA_ALERT_UUID, params.alertUuid)
                putExtra(EXTRA_OCCURRED_AT, params.occurredAtIso)
                putExtra(EXTRA_SEVERITY, params.severity.name)
                putExtra(EXTRA_P_CRASH, params.pCrash)
                putExtra(EXTRA_PEAK_ACCEL_G, params.peakAccelG)
                putExtra(EXTRA_LAT, params.lat)
                putExtra(EXTRA_LON, params.lon)
                putExtra(EXTRA_ACCURACY_M, params.accuracyM)
                putExtra(EXTRA_HEADING_DEG, params.headingDeg)
                putExtra(EXTRA_SPEED_KMH, params.speedKmh)
            }
    }
}
