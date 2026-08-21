package com.rrx.app.ui.drivemode

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.TelemetryFontFamily
import com.rrx.coresensing.DriveSessionState

/**
 * UX-APPFLOW.md §13's Drive Mode. Manually opened from `DriveSection`
 * while sensing is active, not auto-launched on `IN_VEHICLE` -- the
 * spec's own text says screen-on is "optional," and auto-launching an
 * Activity from `DriveSensingService`'s background context hits the same
 * restriction `CrashTriggerNotifier`'s doc comment already covers, which
 * this pass doesn't re-solve for a screen that's allowed to just stay
 * closed. Road-name-from-map-matching (§13's status-bar spec) isn't built
 * either -- `district`/`road_class` off the nearest [com.rrx.app.network.dto.RiskContextDto]
 * are shown instead, real fields, not a fabricated street name. The map
 * itself, including the heading marker and Milestone Marker proxy, lives
 * in [DriveModeMap].
 */
@Composable
fun DriveModeScreen(viewModel: DriveModeViewModel = hiltViewModel()) {
    val sessionState by viewModel.sessionState.collectAsState()
    val nearby by viewModel.nearbySegments.collectAsState()
    val lastFetchedAtMs by viewModel.lastFetchedAtMs.collectAsState()
    val fetchFailed by viewModel.fetchFailed.collectAsState()

    val isLive = !fetchFailed && lastFetchedAtMs?.let { System.currentTimeMillis() - it < LIVE_THRESHOLD_MS } == true
    val sensing = sessionState as? DriveSessionState.Sensing

    // A local val, not sensing?.gpsFix re-read inline below -- Kotlin's
    // smart-cast doesn't carry a null-check on a chained property through
    // to a second use when that property is declared in a different
    // Gradle module (GpsFix/DriveSessionState live in core-sensing), the
    // same cross-module smart-cast limitation TransportSection.kt hit
    // earlier in this project.
    val fix = sensing?.gpsFix

    Column(modifier = Modifier.fillMaxSize().background(Bitumen000)) {
        StatusBar(sensing, nearby.firstOrNull())

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            DriveModeMap(
                segments = nearby.map { it.risk },
                driverFix = fix,
                modifier = Modifier.fillMaxSize(),
            )
        }

        SegmentRibbon(nearby = nearby, isLive = isLive, modifier = Modifier.padding(12.dp))
    }
}

private const val LIVE_THRESHOLD_MS = 30_000L

@Composable
private fun StatusBar(sensing: DriveSessionState.Sensing?, nearest: NearbySegment?) {
    Row(
        modifier = Modifier.fillMaxWidth().height(44.dp).padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text("● ACTIVE", color = Highway300, fontFamily = TelemetryFontFamily)
        Text(
            sensing?.speedKmh?.let { "%.0f km/h".format(it) } ?: "-- km/h",
            color = InkInverse,
            fontFamily = TelemetryFontFamily,
        )
        Text(
            nearest?.risk?.district ?: nearest?.risk?.roadClass ?: "unknown road",
            color = Paper100.copy(alpha = 0.7f),
            fontFamily = TelemetryFontFamily,
        )
    }
}
