package com.rrx.app.ui.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.rrx.app.R
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Bitumen200
import com.rrx.app.ui.theme.Flare500
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.Sodium500
import com.rrx.app.ui.theme.TypeOverline

/** UX-APPFLOW.md §11.3's shared Consent Card template -- one composable,
 * three call sites (Location/Motion/SMS below), so the "same template
 * every time" requirement is structural, not just a copy-paste
 * convention that could drift between the three screens. */
@Composable
fun ConsentCardScreen(
    overline: String,
    reason: String,
    doList: List<String>,
    dontList: List<String>,
    whatWeStore: String,
    allowLabel: String,
    extraLine: String? = null,
    onAllow: () -> Unit,
    onNotNow: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bitumen000)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
    ) {
        Text(overline, style = TypeOverline, color = Sodium500)
        Text(
            reason,
            color = InkInverse,
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(top = 8.dp, bottom = 20.dp),
        )

        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            doList.forEach { Text("✓  $it", color = Highway300) }
            // UX-APPFLOW.md §11.3: "The ✕ list ... is the most important
            // element on the screen." Rendered after the ✓ list but in
            // flare-500 so it still reads first by colour, matching the
            // spec's own reasoning without needing a second visual pass.
            dontList.forEach { Text("✕  $it", color = Flare500) }
        }

        Column(
            modifier = Modifier
                .padding(top = 20.dp)
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(Bitumen200)
                .padding(16.dp),
        ) {
            Text("WHAT WE STORE", style = TypeOverline, color = Paper100.copy(alpha = 0.6f))
            Text(whatWeStore, color = Paper100, modifier = Modifier.padding(top = 4.dp))
        }

        if (extraLine != null) {
            Text(
                extraLine,
                color = Paper100.copy(alpha = 0.7f),
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.padding(top = 16.dp),
            )
        }

        Button(
            onClick = onAllow,
            modifier = Modifier.padding(top = 24.dp).fillMaxWidth().height(56.dp),
        ) {
            Text(allowLabel)
        }
        OutlinedButton(
            onClick = onNotNow,
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Paper100.copy(alpha = 0.6f)),
            modifier = Modifier.padding(top = 8.dp).fillMaxWidth().height(48.dp),
        ) {
            Text(stringResource(R.string.consent_not_now))
        }
    }
}
