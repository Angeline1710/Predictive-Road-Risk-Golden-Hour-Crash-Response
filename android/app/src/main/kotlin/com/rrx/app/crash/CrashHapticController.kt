package com.rrx.app.crash

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/** UX-APPFLOW.md §15.3: "Continuous 200ms pulse per second, synchronised
 * to the numeral" -- a 200ms vibrate / 800ms pause waveform (1s period),
 * looped from index 0 until [stop] is called. */
class CrashHapticController(context: Context) {

    private val vibrator: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }

    fun start() {
        val pattern = longArrayOf(0, 200, 800)
        vibrator?.vibrate(VibrationEffect.createWaveform(pattern, 0))
    }

    fun stop() {
        vibrator?.cancel()
    }
}
