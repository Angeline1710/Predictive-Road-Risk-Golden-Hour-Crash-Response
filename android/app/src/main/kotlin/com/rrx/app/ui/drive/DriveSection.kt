package com.rrx.app.ui.drive

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.rrx.app.ui.drivemode.DriveModeActivity
import com.rrx.coredetection.CrashPrediction
import com.rrx.coresensing.DriveSessionState

private fun requiredPermissions(): Array<String> = buildList {
    add(Manifest.permission.ACCESS_FINE_LOCATION)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) add(Manifest.permission.ACTIVITY_RECOGNITION)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) add(Manifest.permission.POST_NOTIFICATIONS)
}.toTypedArray()

/**
 * Start/stop [com.rrx.coresensing.DriveSensingService] and show its live
 * Stage-A gate state -- a debug readout, not UX-APPFLOW.md §13's actual
 * Drive Mode screen. Once sensing is active, "Open Drive Mode" launches
 * the real thing ([com.rrx.app.ui.drivemode.DriveModeScreen]: live risk
 * map, Segment Ribbon). Risk Warning (§14: voice/haptic/overlay on
 * entering a High/Severe segment) isn't built yet -- see
 * `android/README.md`.
 */
@Composable
fun DriveSection(viewModel: DriveViewModel = hiltViewModel()) {
    val context = LocalContext.current
    val state by viewModel.sessionState.collectAsState()
    val prediction by viewModel.prediction.collectAsState()

    var hasPermissions by remember {
        mutableStateOf(
            requiredPermissions().all {
                ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
            }
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
        hasPermissions = granted.values.all { it }
    }

    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        HorizontalDivider()
        Text("Drive Mode (core-sensing)", style = MaterialTheme.typography.titleMedium)

        if (!hasPermissions) {
            Text(
                "Needs location and activity-recognition permission to sense driving.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(onClick = { permissionLauncher.launch(requiredPermissions()) }) {
                Text("Grant permissions")
            }
        } else {
            when (state) {
                is DriveSessionState.Idle -> Button(onClick = viewModel::startSensing) { Text("Start sensing") }
                is DriveSessionState.Unavailable -> Text(
                    "Unavailable: ${(state as DriveSessionState.Unavailable).reason}",
                    color = MaterialTheme.colorScheme.error,
                )
                else -> {
                    DriveStateReadout(state)
                    prediction?.let { PredictionReadout(it) }
                    Button(onClick = { context.startActivity(DriveModeActivity.intentFor(context)) }) {
                        Text("Open Drive Mode (live risk map)")
                    }
                    Button(onClick = viewModel::stopSensing) { Text("Stop sensing") }
                }
            }
        }
    }
}

@Composable
private fun DriveStateReadout(state: DriveSessionState) {
    Column(modifier = Modifier.padding(vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        when (state) {
            is DriveSessionState.WarmingUp -> Text(
                "Warming up (filling the 4s IMU window)…",
                style = MaterialTheme.typography.labelSmall,
            )
            is DriveSessionState.Sensing -> {
                Text("peak |a| = %.2f g".format(state.peakAccelG), style = MaterialTheme.typography.labelSmall)
                Text(
                    text = state.speedKmh?.let { "speed = %.1f km/h".format(it) } ?: "speed = no GPS fix",
                    style = MaterialTheme.typography.labelSmall,
                )
                Text(
                    "Stage-A: full=${state.stageA.full} degraded=${state.stageA.degraded}",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (state.stageA.degraded) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onBackground,
                )
            }
            else -> Unit
        }
    }
}

/**
 * The most recent [CrashPrediction] from a Stage-A trigger. `raw_audio` is
 * always noise, never a real microphone signal, in this build -- see
 * CrashClassifier's doc comment -- so this number is IMU/GPS-driven only,
 * consistent with `ml/MODELS.md`'s validated no-audio condition.
 */
@Composable
private fun PredictionReadout(prediction: CrashPrediction) {
    Column(modifier = Modifier.padding(vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            "Last classification: p_crash=%.3f severity=%s".format(prediction.pCrash, prediction.severity),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.error,
        )
    }
}
