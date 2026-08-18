package com.rrx.app.crash

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rrx.app.ui.theme.Bitumen050
import com.rrx.app.ui.theme.DisplayFontFamily
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.Paper100

/**
 * UX-APPFLOW.md §16. "Ground snaps to bitumen-050 in 120ms -- the amber
 * leaving the screen *is* the confirmation." The feedback micro-survey
 * ("Help us improve -- what happened?") is out of scope for this pass --
 * genuinely valuable (PRD §7.1's hard-negative pipeline surfaced as one
 * tap) but a separate, self-contained addition, not needed to prove the
 * cancel path itself works. Auto-return-to-Drive-Mode timing is owned by
 * the hosting Activity, not this composable.
 */
@Composable
fun CancelledScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bitumen050)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("✓", color = Highway300, fontSize = 48.sp)
        Text(
            "Alert cancelled",
            color = Paper100,
            fontFamily = DisplayFontFamily,
            fontWeight = FontWeight.SemiBold,
            fontSize = 36.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 12.dp),
        )
        Text(
            "No one was contacted. Drive safe.",
            color = Paper100.copy(alpha = 0.7f),
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp),
        )
    }
}
