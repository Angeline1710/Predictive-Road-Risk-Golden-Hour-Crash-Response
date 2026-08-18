package com.rrx.app.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

/**
 * The scaffold's one real screen: registers this device against the live
 * backend and shows the result. Everything else in PRD.md §13-19 (Drive
 * Mode, the cancel window, onboarding) is out of scope for task #18 --
 * see MVP-PLAN.md §3.3 for what's left and its cost.
 */
@Composable
fun HomeScreen(viewModel: HomeViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
        ) {
            Text("Road-Risk & Golden-Hour Response", style = MaterialTheme.typography.headlineMedium)
            Text(
                "Android scaffold -- proves the toolchain and the device-registration " +
                    "contract against the real backend. Sensing, detection, and transport " +
                    "are not implemented yet.",
                style = MaterialTheme.typography.bodyMedium,
            )

            when (val s = state) {
                is RegistrationState.Idle -> Button(onClick = viewModel::registerDevice) {
                    Text("Register device")
                }
                is RegistrationState.InFlight -> Text("Registering…", style = MaterialTheme.typography.bodyLarge)
                is RegistrationState.Registered -> Text(
                    "Registered. device_id = ${s.deviceId}",
                    style = MaterialTheme.typography.labelSmall,
                )
                is RegistrationState.Failed -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Registration failed: ${s.message}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error,
                    )
                    Button(onClick = viewModel::registerDevice) { Text("Retry") }
                }
            }
        }
    }
}
