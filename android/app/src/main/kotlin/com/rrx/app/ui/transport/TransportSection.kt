package com.rrx.app.ui.transport

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

/**
 * core-transport's one real UI surface in this scaffold: sends a
 * `is_simulated = true` test alert through [com.rrx.coretransport.AlertTransport]
 * against the live backend. Never wired to a real Stage-A trigger --
 * that needs the cancel-window screen (unbuilt) to produce a genuine,
 * user-confirmed payload first.
 */
@Composable
fun TransportSection(viewModel: TransportViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        HorizontalDivider()
        Text("Transport (core-transport, simulated)", style = MaterialTheme.typography.titleMedium)

        when (val s = state) {
            is SendState.Idle -> Button(onClick = viewModel::sendTestAlert) { Text("Send test alert") }
            is SendState.Sending -> Text("Sending…", style = MaterialTheme.typography.bodyMedium)
            is SendState.Done -> {
                val https = s.result.httpsResponse
                Text(
                    "HTTPS: ${if (https != null) "delivered (${https.status})" else "failed/timed out"}",
                    style = MaterialTheme.typography.labelSmall,
                )
                Text(
                    "SMS: ${s.result.smsSent?.let { if (it) "sent" else "failed" } ?: "not attempted"}",
                    style = MaterialTheme.typography.labelSmall,
                )
                Button(onClick = viewModel::sendTestAlert) { Text("Send another") }
            }
        }
    }
}
