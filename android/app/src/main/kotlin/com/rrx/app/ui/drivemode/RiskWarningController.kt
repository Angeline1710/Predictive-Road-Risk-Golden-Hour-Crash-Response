package com.rrx.app.ui.drivemode

import android.content.Context
import android.media.AudioAttributes
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * UX-APPFLOW.md §14: voice at High and above (FR-4.2), plus a double
 * haptic pulse for Severe. Deliberately NOT routed through
 * [com.rrx.app.crash.CrashAudioController]'s `STREAM_ALARM`/DND-bypassing
 * setup -- §14 frames silence at Low/Moderate as the restraint that earns
 * the driver's trust for the bands that do speak ("an app that speaks
 * constantly gets muted"), and nothing in the spec asks for a
 * Do-Not-Disturb override the way an active crash does. TTS here uses
 * `USAGE_ASSISTANCE_NAVIGATION_GUIDANCE`, the same audio attribute a
 * turn-by-turn nav app's voice prompts use: audible in normal ringer
 * mode, silent when the phone is silenced -- same as a missed turn
 * prompt would be, not a siren.
 *
 * "The user's language" is English only, same documented gap as
 * `CrashAudioController` (5-language support is onboarding's job, not
 * wired into any spoken-warning path yet).
 */
class RiskWarningController(context: Context) {
    private val appContext = context.applicationContext
    private var tts: TextToSpeech? = null
    @Volatile private var ttsReady = false

    private val vibrator: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        (appContext.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
    } else {
        @Suppress("DEPRECATION")
        appContext.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }

    init {
        tts = TextToSpeech(appContext) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                tts?.language = Locale.ENGLISH
                tts?.setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
            }
        }
    }

    /** FR-4.2/FR-4.6: one voice line per qualifying segment entry, stating
     * the top contributing factor. `QUEUE_FLUSH` so a slow-to-finish prior
     * utterance can't overlap a fresh one. */
    fun speak(text: String) {
        if (ttsReady) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "risk_warning")
    }

    /** §14 Severe: "double haptic" -- two short pulses, distinct from
     * [com.rrx.app.crash.CrashHapticController]'s continuous per-second
     * loop, which is a different pattern for a different (in-crash)
     * situation. */
    fun doublePulse() {
        val pattern = longArrayOf(0, 120, 120, 120)
        vibrator?.vibrate(VibrationEffect.createWaveform(pattern, -1))
    }

    fun release() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
    }
}
