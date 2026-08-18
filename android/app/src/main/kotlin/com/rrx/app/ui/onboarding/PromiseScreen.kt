package com.rrx.app.ui.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.rrx.app.R
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Bitumen100
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.TypeDisplay1

/** UX-APPFLOW.md §11.1. The Milestone Marker motif and the 4%
 * bottom-radial sodium gradient are both skipped -- neither is expressible
 * without a real asset/shader budget this pass doesn't have; a flat
 * `bitumen-000` ground carries the screen's actual job (the headline)
 * fine on its own. */
@Composable
fun PromiseScreen(onNext: () -> Unit) {
    var showExplainer by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize().background(Bitumen000)) {
        Column(
            modifier = Modifier.fillMaxSize().padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                stringResource(R.string.onboarding_promise_headline),
                style = TypeDisplay1,
                color = InkInverse,
                textAlign = TextAlign.Center,
            )
            Text(
                stringResource(R.string.onboarding_promise_sub),
                color = Paper100.copy(alpha = 0.8f),
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 16.dp),
            )
            Button(
                onClick = onNext,
                modifier = Modifier.padding(top = 40.dp).fillMaxWidth().height(56.dp),
            ) {
                Text(stringResource(R.string.onboarding_promise_cta))
            }
            Text(
                stringResource(R.string.onboarding_promise_how),
                color = Paper100.copy(alpha = 0.6f),
                modifier = Modifier.padding(top = 16.dp).clickable { showExplainer = true },
            )
        }
    }

    if (showExplainer) {
        Dialog(onDismissRequest = { showExplainer = false }) {
            Column(
                modifier = Modifier.clip(RoundedCornerShape(16.dp)).background(Bitumen100).padding(24.dp),
            ) {
                // A plain-language explainer, not the full 4-panel
                // illustrated version §11.1 describes -- that needs real
                // artwork this pass doesn't have.
                Text("How this works", color = Paper100, style = MaterialTheme.typography.titleMedium)
                Text(
                    "Your phone watches its own motion sensors for a crash-like impact. " +
                        "If one happens, a short countdown lets you cancel. If you don't, " +
                        "it sends your location and a short summary to emergency services -- " +
                        "over the internet if it can, over SMS if it can't.",
                    color = Paper100.copy(alpha = 0.85f),
                    modifier = Modifier.padding(top = 12.dp),
                )
                Button(onClick = { showExplainer = false }, modifier = Modifier.padding(top = 20.dp).fillMaxWidth()) {
                    Text("Close")
                }
            }
        }
    }
}
