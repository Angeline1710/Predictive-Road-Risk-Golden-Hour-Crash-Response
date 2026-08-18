package com.rrx.app.ui.onboarding

import android.content.Intent
import android.speech.tts.TextToSpeech
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.rrx.app.R
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Bitumen200
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.Sodium500
import com.rrx.app.ui.theme.TypeCaption
import com.rrx.app.ui.theme.TypeHeading2
import java.util.Locale

/** UX-APPFLOW.md §11.2. */
@Composable
fun LanguageScreen(viewModel: OnboardingViewModel) {
    val selected by viewModel.selectedLanguage.collectAsState()
    val player = rememberLanguagePreviewPlayer()
    val previewLine = stringResource(R.string.onboarding_language_preview_line)

    Column(modifier = Modifier.fillMaxSize().background(Bitumen000).padding(24.dp)) {
        Text(stringResource(R.string.onboarding_language_title), style = TypeHeading2, color = InkInverse)
        Text(
            stringResource(R.string.onboarding_language_subtitle),
            style = TypeCaption,
            color = Paper100.copy(alpha = 0.6f),
            modifier = Modifier.padding(top = 4.dp, bottom = 16.dp),
        )

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            OnboardingLanguages.forEach { language ->
                LanguageRow(
                    language = language,
                    isSelected = language == selected,
                    player = player,
                    previewLine = previewLine,
                    onSelect = { viewModel.selectLanguage(language) },
                )
            }
        }

        Button(
            onClick = viewModel::advance,
            modifier = Modifier.padding(top = 24.dp).fillMaxWidth().height(56.dp),
        ) {
            Text(stringResource(R.string.onboarding_language_continue))
        }
    }
}

@Composable
private fun LanguageRow(
    language: OnboardingLanguage,
    isSelected: Boolean,
    player: LanguagePreviewPlayer,
    previewLine: String,
    onSelect: () -> Unit,
) {
    val context = LocalContext.current
    val locale = language.tag?.let { Locale.forLanguageTag(it) } ?: Locale.ENGLISH
    val voiceAvailable = player.isVoiceAvailable(locale)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(64.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(if (isSelected) Bitumen200 else Bitumen200.copy(alpha = 0.3f))
            .then(
                if (isSelected) Modifier.border(2.dp, Sodium500, RoundedCornerShape(8.dp)) else Modifier
            )
            .clickable(onClick = onSelect)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(language.nativeName, style = TypeHeading2, color = InkInverse)
            Text(language.englishName, style = TypeCaption, color = Paper100.copy(alpha = 0.6f))
        }

        if (voiceAvailable) {
            IconButton(onClick = { player.speak(locale, previewLine) }, modifier = Modifier.size(40.dp)) {
                Box(
                    modifier = Modifier.size(32.dp).clip(CircleShape).background(Sodium500),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("▶", color = Bitumen000, style = MaterialTheme.typography.bodyMedium)
                }
            }
        } else {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(Sodium500)
                    .clickable {
                        context.startActivity(Intent(TextToSpeech.Engine.ACTION_INSTALL_TTS_DATA))
                    }
                    .padding(horizontal = 8.dp, vertical = 4.dp),
            ) {
                Text(
                    stringResource(R.string.onboarding_language_voice_pack_needed),
                    style = MaterialTheme.typography.labelSmall,
                    color = Bitumen000,
                )
            }
        }
    }
}
