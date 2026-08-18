package com.rrx.app.crash

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rrx.app.ui.theme.Bitumen050
import com.rrx.app.ui.theme.CrashButtonLabel
import com.rrx.app.ui.theme.DisplayFontFamily
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Sodium500
import com.rrx.app.ui.theme.Sodium600
import com.rrx.app.ui.theme.Sodium700
import com.rrx.app.ui.theme.TelemetryFontFamily
import com.rrx.coredetection.IncidentSeverity

/**
 * UX-APPFLOW.md §15.2-15.3: full-bleed amber, a countdown numeral legible
 * "by someone who cannot read the language, because it is a digit," and
 * exactly one control. `onCancelRequested` is wired to both this button
 * and, from the hosting Activity, the volume keys.
 */
@Composable
fun CrashCountdownScreen(ui: CountdownUiState, onCancelRequested: () -> Unit) {
    val isCritical = ui.severity == IncidentSeverity.CRITICAL
    val ground = if (isCritical) Sodium600 else Sodium500
    val buttonFill by animateFloatAsState(
        targetValue = if (ui.buttonEnabled) 1f else 0f,
        animationSpec = tween(800),
        label = "cancel-button-enable-fill",
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ground)
            .padding(horizontal = 24.dp, vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        // §15.4: only SEVERE gains the overline label; CRITICAL's own
        // distinguishing treatment is the ground colour + sub-line below,
        // not an additional overline the spec doesn't call for.
        if (ui.severity == IncidentSeverity.SEVERE) {
            Text(
                "SEVERE IMPACT",
                color = InkInverse,
                fontFamily = TelemetryFontFamily,
                fontWeight = FontWeight.SemiBold,
                fontSize = 13.sp,
                letterSpacing = 1.sp,
            )
        }

        Text(
            "CRASH DETECTED",
            color = InkInverse,
            fontFamily = DisplayFontFamily,
            fontWeight = FontWeight.SemiBold,
            fontSize = 36.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp),
        )

        Box(modifier = Modifier.weight(1f), contentAlignment = Alignment.Center) {
            // The single most important glyph in the product (§15.3) --
            // 200sp is the spec's literal size; it changes with no
            // transition, on purpose (a fade/scale here is decoration
            // budget this screen doesn't have).
            Text(
                ui.secondsRemaining.toString(),
                color = InkInverse,
                fontFamily = DisplayFontFamily,
                fontWeight = FontWeight.SemiBold,
                fontSize = 200.sp,
            )
        }

        Text(
            if (isCritical) "Serious impact detected. Sending now." else "Sending alert to emergency services.",
            color = InkInverse,
            style = MaterialTheme.typography.titleMedium,
            textAlign = TextAlign.Center,
        )

        // Drain bar -- redundant time encoding for anyone who can't parse
        // the numeral fast enough under stress (§15.3).
        val fraction = if (ui.totalSeconds > 0) ui.secondsRemaining / ui.totalSeconds.toFloat() else 0f
        Box(
            modifier = Modifier
                .padding(top = 20.dp)
                .fillMaxWidth()
                .height(12.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(Bitumen050.copy(alpha = 0.25f)),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(fraction.coerceIn(0f, 1f))
                    .background(InkInverse),
            )
        }

        // The one control. §15.3: 96dp tall, bitumen-050 fill, visible
        // and readable from frame one -- only its activation is delayed
        // 800ms (shown by the sodium-700 fill), never its visibility.
        // CrashCountdownViewModel.cancel() re-enforces the same
        // buttonEnabled gate regardless of what's clickable here.
        Box(
            modifier = Modifier
                .padding(top = 24.dp)
                .fillMaxWidth()
                .height(96.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Bitumen050)
                .clickable(enabled = ui.buttonEnabled, onClick = onCancelRequested),
            contentAlignment = Alignment.Center,
        ) {
            Box(
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .fillMaxHeight()
                    .fillMaxWidth(buttonFill)
                    .background(Sodium700.copy(alpha = 0.35f)),
            )
            Text(
                "I'M OK — CANCEL",
                color = CrashButtonLabel,
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp,
                letterSpacing = 1.sp,
            )
        }

        Text(
            "or press any volume button",
            color = InkInverse.copy(alpha = 0.7f),
            fontSize = 12.sp,
            modifier = Modifier.padding(top = 12.dp),
        )
    }
}
