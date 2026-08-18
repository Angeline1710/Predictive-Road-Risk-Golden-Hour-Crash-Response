package com.rrx.app.ui.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rrx.app.R
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.Highway700
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.TelemetryFontFamily
import com.rrx.app.ui.theme.TypeDisplay1

/** UX-APPFLOW.md §11.6, Step 9. */
@Composable
fun ReadyScreen(viewModel: OnboardingViewModel) {
    val selectedLanguage by viewModel.selectedLanguage.collectAsState()

    Column(
        modifier = Modifier.fillMaxSize().background(Highway700).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("✓", color = Highway300, fontSize = 64.sp)
        Text(
            stringResource(R.string.onboarding_ready_headline),
            style = TypeDisplay1,
            color = InkInverse,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 16.dp),
        )

        Column(modifier = Modifier.padding(top = 24.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                stringResource(R.string.onboarding_ready_status_detection),
                color = Highway300,
                fontFamily = TelemetryFontFamily,
            )
            Text(
                // The status line is honest about what was actually
                // granted -- not a blanket "protected" claim regardless
                // of what happened on the SMS consent card.
                if (viewModel.smsConsentGranted()) {
                    stringResource(R.string.onboarding_ready_status_fallback_live)
                } else {
                    stringResource(R.string.onboarding_ready_status_fallback_off)
                },
                color = Highway300,
                fontFamily = TelemetryFontFamily,
            )
            Text(
                stringResource(R.string.onboarding_ready_status_language, selectedLanguage.englishName),
                color = Highway300,
                fontFamily = TelemetryFontFamily,
            )
        }

        Button(
            onClick = viewModel::advance,
            modifier = Modifier.padding(top = 32.dp).fillMaxWidth().height(56.dp),
        ) {
            Text(stringResource(R.string.onboarding_ready_done))
        }
    }
}
