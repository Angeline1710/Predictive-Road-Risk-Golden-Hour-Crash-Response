package com.rrx.app.ui.drive

import android.app.Application
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.app.crash.CrashTriggerNotifier
import com.rrx.app.network.RrxApi
import com.rrx.app.ui.drivemode.NearbySegment
import com.rrx.app.ui.drivemode.RiskBand
import com.rrx.app.ui.drivemode.distanceToNearestVertexM
import com.rrx.coredetection.CrashClassifier
import com.rrx.coredetection.CrashPrediction
import com.rrx.coredetection.TabularFeatures
import com.rrx.coresensing.DriveSensingBus
import com.rrx.coresensing.DriveSensingService
import com.rrx.coresensing.DriveSessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.stateIn
import java.util.concurrent.atomic.AtomicBoolean
import javax.inject.Inject
import kotlin.math.roundToInt

/**
 * Thin wrapper over [DriveSensingBus] and [DriveSensingService]'s
 * start/stop lifecycle, plus the glue core-sensing and core-detection
 * don't have themselves: on the rising edge of Stage-A's degraded arm
 * (see [com.rrx.coresensing.StageAGate]), extracts tabular features and
 * runs [CrashClassifier] once, off the main thread. Edge-triggered, not
 * level-triggered -- classification is real inference work, not something
 * to re-run every 200ms evaluation tick while a gate stays open.
 *
 * Also owns UX-APPFLOW.md §13's ambient (screen-off) notification content
 * -- see [maybeUpdateAmbientNotification]'s doc comment for why this,
 * a ViewModel, is the right place for a "keeps running whether or not a
 * screen is open" concern: this project already accepts that exact
 * lifecycle assumption for crash detection above, via the same
 * `sessionState` collection.
 */
@HiltViewModel
class DriveViewModel @Inject constructor(
    private val application: Application,
    private val api: RrxApi,
) : AndroidViewModel(application) {

    private val classifierLazy = lazy { CrashClassifier(application) }
    private var wasStageATriggered = false

    // TFLite's Interpreter is documented as not safe for concurrent
    // invocation on the same instance. A single rising edge can only ever
    // launch one classify() coroutine, but a real crash can plausibly
    // produce a second rising edge (a secondary impact) before the first
    // classification finishes; without this guard that would be two
    // concurrent calls into the same Interpreter.
    private val isClassifying = AtomicBoolean(false)

    private val _prediction = MutableStateFlow<CrashPrediction?>(null)
    val prediction: StateFlow<CrashPrediction?> = _prediction.asStateFlow()

    val sessionState: StateFlow<DriveSessionState> = DriveSensingBus.state
        .onEach(::maybeClassify)
        .onEach(::maybeUpdateAmbientNotification)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), DriveSessionState.Idle)

    private fun maybeClassify(state: DriveSessionState) {
        if (state !is DriveSessionState.Sensing) {
            wasStageATriggered = false
            return
        }
        val triggered = state.stageA.degraded
        val gpsWindow = state.gpsWindow
        if (triggered && !wasStageATriggered && gpsWindow != null && isClassifying.compareAndSet(false, true)) {
            viewModelScope.launch(Dispatchers.Default) {
                try {
                    val tab = TabularFeatures.extract(state.imuWindow, state.accelRailG, gpsWindow)
                    val prediction = classifierLazy.value.classify(state.imuWindow, gpsWindow, tab)
                    _prediction.value = prediction
                    CrashTriggerNotifier.maybeTrigger(application, state, prediction)
                } finally {
                    isClassifying.set(false)
                }
            }
        }
        wasStageATriggered = triggered
    }

    // Same shape as DriveModeViewModel's own refetch throttle, tuned looser:
    // this runs continuously in the background whenever sensing is active,
    // not just while a screen is open, so it deliberately polls less often
    // to keep the battery cost PRD §12.1 cares about small. Kept separate
    // from DriveModeViewModel's version rather than shared -- the two have
    // different cadence requirements and different lifecycles (this one
    // must keep running past this ViewModel's own screen closing, exactly
    // like maybeClassify's crash-detection path above already assumes).
    private var lastAmbientFetchLat: Double? = null
    private var lastAmbientFetchLon: Double? = null
    private var lastAmbientFetchAtMs = 0L
    private var isAmbientFetching = false
    private var lastAmbientNearby: List<NearbySegment> = emptyList()

    private fun maybeUpdateAmbientNotification(state: DriveSessionState) {
        val sensing = state as? DriveSessionState.Sensing
        if (sensing == null) {
            lastAmbientFetchLat = null
            lastAmbientFetchLon = null
            lastAmbientNearby = emptyList()
            return
        }
        val fix = sensing.gpsFix
        if (fix == null) {
            renderAmbientNotification(sensing.speedKmh, emptyList())
            return
        }

        val movedFarEnough = lastAmbientFetchLat == null ||
            distanceToNearestVertexM(fix.lat, fix.lon, listOf(listOf(lastAmbientFetchLon!!, lastAmbientFetchLat!!))) > AMBIENT_REFETCH_DISTANCE_M
        val stale = System.currentTimeMillis() - lastAmbientFetchAtMs > AMBIENT_REFETCH_INTERVAL_MS
        if (isAmbientFetching || (!movedFarEnough && !stale)) {
            renderAmbientNotification(sensing.speedKmh, lastAmbientNearby)
            return
        }

        isAmbientFetching = true
        lastAmbientFetchLat = fix.lat
        lastAmbientFetchLon = fix.lon
        lastAmbientFetchAtMs = System.currentTimeMillis()
        viewModelScope.launch {
            try {
                val segments = api.riskBbox(
                    minLat = fix.lat - AMBIENT_BBOX_HALF_DEGREES, minLon = fix.lon - AMBIENT_BBOX_HALF_DEGREES,
                    maxLat = fix.lat + AMBIENT_BBOX_HALF_DEGREES, maxLon = fix.lon + AMBIENT_BBOX_HALF_DEGREES,
                )
                lastAmbientNearby = segments
                    .map { NearbySegment(it, distanceToNearestVertexM(fix.lat, fix.lon, it.geometry), RiskBand.fromApi(it.band)) }
                    .sortedBy { it.distanceM }
            } catch (e: Exception) {
                // Keep showing the last-known nearby list rather than blank
                // the notification -- same "never mistake stale for
                // missing" posture Drive Mode's own map/ribbon use for a
                // failed /risk/bbox refetch.
            } finally {
                isAmbientFetching = false
            }
            renderAmbientNotification(sensing.speedKmh, lastAmbientNearby)
        }
    }

    /** UX-APPFLOW.md §13's ambient notification content: live speed, the
     * nearest road/district (real fields; road-name-from-map-matching
     * isn't built, same honest gap DriveModeScreen's StatusBar has), and
     * the next notable (High/Severe) segment ahead -- mirrors
     * SegmentRibbon.kt's `nextNotable` line exactly. Posts to the SAME
     * notification id/channel [DriveSensingService] created when it
     * called `startForeground()`; updating a foreground service's
     * notification from elsewhere in the process is supported and does
     * not need its own POST_NOTIFICATIONS check -- the foreground-service
     * notification is already exempt. */
    private fun renderAmbientNotification(speedKmh: Float?, nearby: List<NearbySegment>) {
        val nearest = nearby.firstOrNull()
        val nextNotable = nearby.firstOrNull { it.band.isNotable }
        val speedText = speedKmh?.let { "%.0f km/h".format(it) } ?: "-- km/h"
        val roadText = nearest?.risk?.district ?: nearest?.risk?.roadClass ?: "unknown road"
        val nextText = nextNotable?.let {
            " · Next: %s in %s".format(
                it.band.name.lowercase().replaceFirstChar { c -> c.uppercase() },
                formatAmbientDistance(it.distanceM),
            )
        } ?: ""

        val notification = NotificationCompat.Builder(application, DriveSensingService.CHANNEL_ID)
            .setContentTitle("Road-Risk Response")
            .setContentText("● Active · $speedText · $roadText$nextText")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .build()
        try {
            NotificationManagerCompat.from(application).notify(DriveSensingService.NOTIFICATION_ID, notification)
        } catch (e: SecurityException) {
            // POST_NOTIFICATIONS revoked mid-session -- the foreground
            // service keeps running with its last-posted notification;
            // this is a best-effort content refresh, not safety-critical.
        }
    }

    private fun formatAmbientDistance(m: Double): String =
        if (m >= 1000) "%.1f km".format(m / 1000) else "${m.roundToInt()} m"

    fun startSensing() = DriveSensingService.start(application)

    fun stopSensing() = DriveSensingService.stop(application)

    override fun onCleared() {
        // classify() has no suspension points, so cancelling viewModelScope
        // does not interrupt an in-flight native call -- closing the
        // interpreter out from under it would be a use-after-close in the
        // native layer. Skipping close() here leaks the interpreter in
        // that narrow window (ViewModel cleared mid-inference) rather than
        // risk that; a real fix needs the close to wait on isClassifying,
        // which is more synchronization than this scaffold's one screen
        // warrants.
        if (classifierLazy.isInitialized() && !isClassifying.get()) {
            classifierLazy.value.close()
        }
        super.onCleared()
    }

    private companion object {
        // ~0.01 deg, matching DriveModeViewModel's own bbox half-width.
        const val AMBIENT_BBOX_HALF_DEGREES = 0.01
        // Looser than DriveModeViewModel's 300m/15s (a live, on-screen map)
        // -- this poll runs whether or not any screen is open, so it trades
        // freshness for battery per PRD §12.1.
        const val AMBIENT_REFETCH_DISTANCE_M = 800.0
        const val AMBIENT_REFETCH_INTERVAL_MS = 45_000L
    }
}
