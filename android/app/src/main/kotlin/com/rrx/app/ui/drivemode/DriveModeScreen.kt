package com.rrx.app.ui.drivemode

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Bitumen200
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.RiskSevere
import com.rrx.app.ui.theme.TelemetryFontFamily
import com.rrx.app.ui.theme.TypeCaption
import com.rrx.app.ui.theme.TypeHeading2
import com.rrx.coresensing.DriveSessionState
import kotlin.math.roundToInt

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
 * in [DriveModeMap]. The Severe risk-warning overlay (UX-APPFLOW.md §14)
 * is a sibling layer over this same layout, driven by
 * [DriveModeViewModel.severeOverlay]; High/Severe's voice line and
 * Severe's double haptic pulse are one-shot side effects fired from
 * [DriveModeViewModel.warningEvents], not overlay state.
 */
@Composable
fun DriveModeScreen(viewModel: DriveModeViewModel = hiltViewModel()) {
    val sessionState by viewModel.sessionState.collectAsState()
    val nearby by viewModel.nearbySegments.collectAsState()
    val lastFetchedAtMs by viewModel.lastFetchedAtMs.collectAsState()
    val fetchFailed by viewModel.fetchFailed.collectAsState()
    val severeOverlay by viewModel.severeOverlay.collectAsState()

    val isLive = !fetchFailed && lastFetchedAtMs?.let { System.currentTimeMillis() - it < LIVE_THRESHOLD_MS } == true
    val sensing = sessionState as? DriveSessionState.Sensing

    // A local val, not sensing?.gpsFix re-read inline below -- Kotlin's
    // smart-cast doesn't carry a null-check on a chained property through
    // to a second use when that property is declared in a different
    // Gradle module (GpsFix/DriveSessionState live in core-sensing), the
    // same cross-module smart-cast limitation TransportSection.kt hit
    // earlier in this project.
    val fix = sensing?.gpsFix

    val context = LocalContext.current
    val warningController = remember { RiskWarningController(context) }
    DisposableEffect(Unit) { onDispose { warningController.release() } }
    LaunchedEffect(viewModel) {
        viewModel.warningEvents.collect { event ->
            warningController.speak(warningLine(event))
            if (event.band == RiskBand.SEVERE) warningController.doublePulse()
        }
    }

    // AnimatedVisibility's exit transition needs something to keep
    // rendering while it slides away; severeOverlay itself goes null the
    // instant the driver exits the segment, which would otherwise blank
    // the card mid-animation instead of sliding its last real content out.
    var lastSevereOverlay by remember { mutableStateOf<SevereOverlayState?>(null) }
    LaunchedEffect(severeOverlay) { severeOverlay?.let { lastSevereOverlay = it } }

    Box(modifier = Modifier.fillMaxSize()) {
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

        AnimatedVisibility(
            visible = severeOverlay != null,
            enter = slideInVertically(animationSpec = tween(280)) { it },
            exit = slideOutVertically(animationSpec = tween(280)) { it },
            modifier = Modifier.align(Alignment.BottomCenter),
        ) {
            lastSevereOverlay?.let { SevereWarningOverlay(it) }
        }
    }
}

/** FR-4.6: states the top contributing factor, not a bare band name. */
private fun warningLine(event: RiskWarningEvent): String {
    val prefix = if (event.band == RiskBand.SEVERE) "Severe risk ahead." else "High risk ahead."
    val topFactor = event.topFactors.firstOrNull() ?: return prefix
    return "$prefix $topFactor."
}

private fun formatDistance(m: Double): String =
    if (m >= 1000) "%.1f km".format(m / 1000) else "${m.roundToInt()} m"

/** UX-APPFLOW.md §14's Severe overlay: slides up 88dp from the bottom,
 * bottom-anchored deliberately (stays out of the mirror-and-road
 * sightline, lands in thumb reach) -- no close button, since "the
 * driver's hands belong on the wheel." */
@Composable
private fun SevereWarningOverlay(state: SevereOverlayState) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(88.dp)
            .background(Bitumen200)
            .drawBehind {
                drawLine(RiskSevere, Offset(0f, 1f), Offset(size.width, 1f), strokeWidth = 2.dp.toPx())
                // A real cross-hatch fill at 6% opacity -- the NFR-A3 hatch
                // pattern RiskBand.kt's own doc comment notes is missing
                // everywhere else in this build; built here since the
                // Severe overlay is the one place the spec calls for it
                // explicitly by name ("cross-hatch texture at 6%").
                val spacing = 14.dp.toPx()
                var x = -size.height
                while (x < size.width) {
                    drawLine(
                        RiskSevere.copy(alpha = 0.06f),
                        Offset(x, size.height), Offset(x + size.height, 0f),
                        strokeWidth = 1.5.dp.toPx(),
                    )
                    x += spacing
                }
            }
            .padding(horizontal = 16.dp),
        contentAlignment = Alignment.CenterStart,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Box(
                modifier = Modifier.size(32.dp).background(RiskSevere, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text("S", color = InkInverse, fontFamily = TelemetryFontFamily, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("SEVERE — ${formatDistance(state.distanceM)} ahead", style = TypeHeading2, color = InkInverse)
                Text(
                    state.topFactors.take(3).joinToString(", "),
                    style = TypeCaption,
                    color = Paper100.copy(alpha = 0.7f),
                )
            }
            Spacer(Modifier.width(12.dp))
            Text(formatDistance(state.distanceM), fontFamily = TelemetryFontFamily, fontSize = 22.sp, color = InkInverse)
        }
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
