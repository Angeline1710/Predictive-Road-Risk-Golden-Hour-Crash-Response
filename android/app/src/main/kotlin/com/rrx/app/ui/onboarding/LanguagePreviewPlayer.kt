package com.rrx.app.ui.onboarding

import android.content.Context
import android.speech.tts.TextToSpeech
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import java.util.Locale

/**
 * UX-APPFLOW.md §11.2: "This is the only chance the user has to hear the
 * alert before it's real." A tiny wrapper around [TextToSpeech], separate
 * from [com.rrx.app.crash.CrashAudioController] since that one is
 * permanently locked to the countdown's per-second numeral announcements
 * on `STREAM_ALARM` -- this one speaks one full sentence, on demand, in
 * whichever language row was tapped, on the normal media stream.
 */
class LanguagePreviewPlayer(context: Context) {
    private var tts: TextToSpeech? = null
    private var ready = false

    init {
        tts = TextToSpeech(context) { status -> ready = status == TextToSpeech.SUCCESS }
    }

    /** UX-APPFLOW.md §11.2: "If the TTS voice pack is missing, the row
     * shows a VOICE PACK NEEDED chip." [TextToSpeech.isLanguageAvailable]
     * is the real signal for that, not a guess. */
    fun isVoiceAvailable(locale: Locale): Boolean {
        val engine = tts ?: return false
        val result = engine.isLanguageAvailable(locale)
        return result == TextToSpeech.LANG_AVAILABLE ||
            result == TextToSpeech.LANG_COUNTRY_AVAILABLE ||
            result == TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE
    }

    fun speak(locale: Locale, text: String) {
        val engine = tts ?: return
        if (!ready) return
        engine.language = locale
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "onboarding_language_preview")
    }

    fun release() {
        tts?.stop()
        tts?.shutdown()
        tts = null
    }
}

@Composable
fun rememberLanguagePreviewPlayer(): LanguagePreviewPlayer {
    val context = LocalContext.current
    val player = remember { LanguagePreviewPlayer(context) }
    DisposableEffect(Unit) { onDispose { player.release() } }
    return player
}
