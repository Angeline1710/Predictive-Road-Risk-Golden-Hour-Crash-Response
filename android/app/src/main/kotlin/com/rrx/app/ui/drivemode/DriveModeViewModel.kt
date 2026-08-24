package com.rrx.app.ui.drivemode

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.app.network.RrxApi
import com.rrx.app.network.dto.RiskContextDto
import com.rrx.coresensing.DriveSensingBus
import com.rrx.coresensing.DriveSessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * UX-APPFLOW.md §13's live risk map, backed by the same `GET /risk/bbox`
 * contract `web/src/lib/api.ts` already calls for the dashboard's Live
 * Operations map -- a second client of a contract already verified
 * against the real backend, not a new one. Refetches around the driver's
 * current position (from [DriveSensingBus], the same live feed
 * [com.rrx.app.ui.drive.DriveViewModel] already consumes) on significant
 * movement or a staleness timeout, whichever comes first.
 */
@HiltViewModel
class DriveModeViewModel @Inject constructor(
    private val api: RrxApi,
) : ViewModel() {

    val sessionState: StateFlow<DriveSessionState> = DriveSensingBus.state

    private val _segments = MutableStateFlow<List<RiskContextDto>>(emptyList())

    private val _lastFetchedAtMs = MutableStateFlow<Long?>(null)
    val lastFetchedAtMs: StateFlow<Long?> = _lastFetchedAtMs.asStateFlow()

    private val _fetchFailed = MutableStateFlow(false)
    val fetchFailed: StateFlow<Boolean> = _fetchFailed.asStateFlow()

    /** Nearby segments sorted by distance from the driver's current
     * position, nearest first -- Segment Ribbon's data source. See
     * [distanceToNearestVertexM]'s doc comment for why "nearby" here is a
     * proxy for "ahead," not the real thing. */
    val nearbySegments: StateFlow<List<NearbySegment>> = combine(sessionState, _segments) { state, segments ->
        val fix = (state as? DriveSessionState.Sensing)?.gpsFix ?: return@combine emptyList()
        segments
            .map { seg -> NearbySegment(seg, distanceToNearestVertexM(fix.lat, fix.lon, seg.geometry), RiskBand.fromApi(seg.band)) }
            .sortedBy { it.distanceM }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    // UX-APPFLOW.md §14 / PRD.md §8.4 (FR-4.2/4.4/4.5): the one-shot voice
    // (+ haptic, for Severe) event DriveModeScreen fires as a side effect.
    // A SharedFlow, not a StateFlow -- each entry is a discrete "this just
    // happened" moment (matching a fresh collector shouldn't replay a stale
    // warning), unlike nearbySegments' continuously-current snapshot.
    private val _warningEvents = MutableSharedFlow<RiskWarningEvent>(extraBufferCapacity = 1)
    val warningEvents: SharedFlow<RiskWarningEvent> = _warningEvents.asSharedFlow()

    private val _severeOverlay = MutableStateFlow<SevereOverlayState?>(null)
    val severeOverlay: StateFlow<SevereOverlayState?> = _severeOverlay.asStateFlow()

    private var lastFetchLat: Double? = null
    private var lastFetchLon: Double? = null
    private var isFetching = false

    // Which segment was nearest as of the last evaluation, regardless of
    // band -- "entering" a High/Severe segment is detected as this value
    // changing while the new nearest segment is notable, not a separate
    // in-segment/out-of-segment state machine.
    private var lastNearestSegmentId: Int? = null
    private var activeSevereSegmentId: Int? = null
    private val lastWarnedAtMs = mutableMapOf<Int, Long>()

    init {
        viewModelScope.launch {
            sessionState.collect { state ->
                val fix = (state as? DriveSessionState.Sensing)?.gpsFix ?: return@collect
                maybeRefetch(fix.lat, fix.lon)
            }
        }
        viewModelScope.launch {
            combine(sessionState, nearbySegments) { state, nearby -> state to nearby }
                .collect { (state, nearby) -> evaluateRiskWarning(state, nearby) }
        }
    }

    private fun evaluateRiskWarning(state: DriveSessionState, nearby: List<NearbySegment>) {
        val nearest = nearby.firstOrNull()
        updateSevereOverlay(nearest)

        val previousSegmentId = lastNearestSegmentId
        lastNearestSegmentId = nearest?.risk?.segmentId
        if (nearest == null || !nearest.band.isNotable) return
        if (nearest.risk.segmentId == previousSegmentId) return   // not a fresh entry

        // FR-4.5: suppress all voice warnings below 25 km/h. Deliberately
        // gates the whole event (voice + haptic + overlay), not just the
        // TTS call -- §14 doesn't separately spec overlay-without-voice
        // behaviour at low speed. Scope simplification, documented rather
        // than silently assumed: entering a notable segment below this
        // speed and later accelerating WITHIN that same segment does not
        // retroactively fire the warning, since the entry edge already
        // passed (unfired) and the segment id hasn't changed since.
        val speedKmh = (state as? DriveSessionState.Sensing)?.speedKmh ?: 0f
        if (speedKmh < SPEED_GATE_KMH) return

        // FR-4.4: suppress repeat warnings for the same segment within 15 min.
        val now = System.currentTimeMillis()
        val last = lastWarnedAtMs[nearest.risk.segmentId]
        if (last != null && now - last < COOLDOWN_MS) return
        lastWarnedAtMs[nearest.risk.segmentId] = now

        _warningEvents.tryEmit(RiskWarningEvent(nearest.risk.segmentId, nearest.band, nearest.risk.topFactors))
        if (nearest.band == RiskBand.SEVERE) {
            activeSevereSegmentId = nearest.risk.segmentId
            _severeOverlay.value = SevereOverlayState(nearest.risk.segmentId, nearest.risk.topFactors, nearest.distanceM)
        }
    }

    /** "Auto-dismisses on exiting the segment" (UX-APPFLOW.md §14) -- runs
     * every evaluation, independent of whether a new warning just fired,
     * so the live distance countdown keeps updating and the overlay
     * disappears the moment the driver is no longer nearest to the
     * triggering segment or its band has dropped below Severe. */
    private fun updateSevereOverlay(nearest: NearbySegment?) {
        val activeId = activeSevereSegmentId ?: return
        if (nearest != null && nearest.risk.segmentId == activeId && nearest.band == RiskBand.SEVERE) {
            _severeOverlay.value = SevereOverlayState(activeId, nearest.risk.topFactors, nearest.distanceM)
        } else {
            activeSevereSegmentId = null
            _severeOverlay.value = null
        }
    }

    private fun maybeRefetch(lat: Double, lon: Double) {
        if (isFetching) return
        val movedFarEnough = lastFetchLat == null ||
            distanceToNearestVertexM(lat, lon, listOf(listOf(lastFetchLon!!, lastFetchLat!!))) > REFETCH_DISTANCE_M
        val stale = _lastFetchedAtMs.value?.let { System.currentTimeMillis() - it > REFETCH_INTERVAL_MS } ?: true
        if (!movedFarEnough && !stale) return

        isFetching = true
        lastFetchLat = lat
        lastFetchLon = lon
        viewModelScope.launch {
            try {
                _segments.value = api.riskBbox(
                    minLat = lat - BBOX_HALF_DEGREES, minLon = lon - BBOX_HALF_DEGREES,
                    maxLat = lat + BBOX_HALF_DEGREES, maxLon = lon + BBOX_HALF_DEGREES,
                )
                _lastFetchedAtMs.value = System.currentTimeMillis()
                _fetchFailed.value = false
            } catch (e: Exception) {
                // §13's "● LIVE / ◐ CACHED" distinction: a failed refetch
                // keeps showing the last-known segments (still in
                // _segments) rather than clearing the map, with
                // staleness surfaced via lastFetchedAtMs instead.
                _fetchFailed.value = true
            } finally {
                isFetching = false
            }
        }
    }

    private companion object {
        // ~0.01 deg is roughly 1.1km at the equator -- a wider box than
        // the driver strictly needs ahead, but simple and symmetric
        // rather than heading-aware (no compass/bearing-weighted query
        // this pass builds).
        const val BBOX_HALF_DEGREES = 0.01
        const val REFETCH_DISTANCE_M = 300.0
        const val REFETCH_INTERVAL_MS = 15_000L

        // PRD.md §8.4.
        const val SPEED_GATE_KMH = 25.0     // FR-4.5
        const val COOLDOWN_MS = 15 * 60 * 1000L   // FR-4.4
    }
}
