package com.rrx.app.crash

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.ToneGenerator
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * UX-APPFLOW.md §15.3's audio requirement: "Escalating two-tone siren at
 * maximum volume, overriding silent and Do Not Disturb, plus TTS counting
 * down in the user's language." Both the tone and the TTS speech are
 * routed to `STREAM_ALARM` -- the one Android stream ringer-mode=silent
 * doesn't touch, which is the platform mechanism this requirement is
 * actually asking for. Full Do Not Disturb override needs the user to
 * separately grant Notification Policy Access (a Settings-mediated
 * permission); that escalation isn't requested here -- STREAM_ALARM alone
 * is standard practice (it's what alarm-clock apps rely on) and doesn't
 * need it.
 *
 * "The user's language" is English only in this build -- 5-language
 * support is onboarding's job (MVP-PLAN.md §3.3), not built yet.
 */
class CrashAudioController(private val context: Context) {

    private var toneGenerator: ToneGenerator? = null
    private var tts: TextToSpeech? = null
    @Volatile private var ttsReady = false

    fun start() {
        toneGenerator = runCatching { ToneGenerator(AudioManager.STREAM_ALARM, ToneGenerator.MAX_VOLUME) }.getOrNull()
        tts = TextToSpeech(context) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                tts?.language = Locale.ENGLISH
                tts?.setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
            }
        }
    }

    /** Called once per second of the countdown -- a short alternating
     * tone burst (the "two-tone" siren) followed by the spoken number,
     * `QUEUE_FLUSH` so a slow-to-finish previous utterance never overlaps
     * and drifts out of sync with the numeral. */
    fun announceSecond(secondsRemaining: Int) {
        val tone = if (secondsRemaining % 2 == 0) ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD else ToneGenerator.TONE_CDMA_ABBR_ALERT
        toneGenerator?.startTone(tone, TONE_DURATION_MS)
        if (ttsReady && secondsRemaining > 0) {
            tts?.speak(secondsRemaining.toString(), TextToSpeech.QUEUE_FLUSH, null, "crash_countdown")
        }
    }

    fun stop() {
        toneGenerator?.release()
        toneGenerator = null
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
    }

    private companion object {
        const val TONE_DURATION_MS = 150
    }
}
