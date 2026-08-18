package com.rrx.app.crash

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rrx.app.ui.theme.Bitumen050
import com.rrx.app.ui.theme.Bitumen100
import com.rrx.app.ui.theme.DisplayFontFamily
import com.rrx.app.ui.theme.Flare500
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.Sodium500
import com.rrx.app.ui.theme.TelemetryFontFamily
import kotlinx.coroutines.delay

/**
 * UX-APPFLOW.md §17, simplified: the real spec is a 4-node channel ladder
 * with per-step timestamps (detected/sent/received/acknowledged).
 * [com.rrx.coretransport.AlertTransport.send] is a single suspend call
 * returning one final [com.rrx.coretransport.TransportResult], not a
 * stream of intermediate progress events, so this shows "sending" then
 * the final per-channel outcome rather than fabricating timestamps for
 * steps this build can't actually observe individually. A real 4-node
 * ladder needs AlertTransport to expose progress as a Flow -- a
 * worthwhile follow-up, not built here.
 *
 * The Simulation Seal is mandatory per UX-APPFLOW.md §7.5/§17's
 * "even in the driver app, even at the most emotionally loaded moment,
 * the mock is disclosed" -- shown unconditionally, since the gateway is
 * always simulated in this build (PRD §11).
 */
@Composable
fun SendingScreen(state: CrashFlowState) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bitumen050)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        when (state) {
            is CrashFlowState.Sending -> {
                CircularProgressIndicator(color = Sodium500)
                Text(
                    "Sending alert…",
                    color = Paper100,
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 16.dp),
                )
            }
            is CrashFlowState.Sent -> SentContent(state)
            else -> Unit
        }
    }
}

@Composable
private fun SentContent(state: CrashFlowState.Sent) {
    val delivered = state.result.delivered
    Text(
        if (delivered) "ALERT SENT" else "DELIVERY UNCERTAIN",
        color = Paper100,
        fontFamily = DisplayFontFamily,
        fontWeight = FontWeight.SemiBold,
        fontSize = 32.sp,
    )

    Column(
        modifier = Modifier
            .padding(top = 16.dp)
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(Bitumen100)
            .padding(16.dp),
    ) {
        val https = state.result.httpsResponse
        Text(
            if (https != null) "✓ Received by server (status: ${https.status})" else "○ HTTPS not delivered",
            color = if (https != null) Highway300 else Flare500,
            fontFamily = TelemetryFontFamily,
            fontSize = 13.sp,
        )
        Text(
            when (state.result.smsSent) {
                true -> "✓ Sent over SMS"
                false -> "○ SMS not delivered"
                null -> "· SMS not attempted"
            },
            color = when (state.result.smsSent) {
                true -> Highway300
                false -> Flare500
                null -> Paper100.copy(alpha = 0.6f)
            },
            fontFamily = TelemetryFontFamily,
            fontSize = 13.sp,
            modifier = Modifier.padding(top = 4.dp),
        )

        val dispatch = https?.dispatch
        if (dispatch != null) {
            Text(
                "Ticket ${dispatch.ticketId ?: "pending"}",
                color = Paper100,
                fontFamily = TelemetryFontFamily,
                fontSize = 13.sp,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }

    // UX-APPFLOW.md §7.5: mandatory, non-dismissible -- v1's gateway is
    // always simulated (PRD §11).
    Column(
        modifier = Modifier
            .padding(top = 12.dp)
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .border(2.dp, Flare500, RoundedCornerShape(8.dp))
            .padding(12.dp),
    ) {
        Text(
            "SIMULATED DISPATCH",
            color = Flare500,
            fontFamily = TelemetryFontFamily,
            fontWeight = FontWeight.Bold,
            fontSize = 12.sp,
        )
        Text(
            "Demonstration mode — this dispatch is simulated.",
            color = Paper100.copy(alpha = 0.8f),
            fontSize = 12.sp,
            modifier = Modifier.padding(top = 2.dp),
        )
    }

    GoldenHourCountup(modifier = Modifier.padding(top = 16.dp))
}

/** Numeral-only Golden Hour readout (UX-APPFLOW.md §7.3's row variant --
 * "72px, numeral only, no label" -- with a label added anyway since this
 * is the one place it appears on this screen, not a dense list). Not the
 * full radial-tick dial; that's a Canvas-drawing task of its own. */
@Composable
private fun GoldenHourCountup(modifier: Modifier = Modifier) {
    var elapsedS by remember { mutableLongStateOf(0L) }
    LaunchedEffect(Unit) {
        val start = System.currentTimeMillis()
        while (true) {
            elapsedS = (System.currentTimeMillis() - start) / 1000
            delay(1_000L)
        }
    }
    val remaining = 3600 - elapsedS
    val display = if (remaining >= 0) {
        "%02d:%02d".format(remaining / 60, remaining % 60)
    } else {
        "+%02d:%02d".format(-remaining / 60, -remaining % 60)
    }
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(display, color = Paper100, fontFamily = TelemetryFontFamily, fontSize = 32.sp)
        Text(
            if (remaining >= 0) "GOLDEN HOUR REMAINING" else "ELAPSED",
            color = Paper100.copy(alpha = 0.6f),
            fontSize = 11.sp,
            letterSpacing = 1.sp,
        )
    }
}
