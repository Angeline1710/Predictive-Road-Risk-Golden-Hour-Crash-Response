package com.rrx.app.ui.drivemode

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.app.network.RrxApi
import com.rrx.app.network.dto.RiskContextDto
import com.rrx.coresensing.DriveSensingBus
import com.rrx.coresensing.DriveSessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
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

    private var lastFetchLat: Double? = null
    private var lastFetchLon: Double? = null
    private var isFetching = false

    init {
        viewModelScope.launch {
            sessionState.collect { state ->
                val fix = (state as? DriveSessionState.Sensing)?.gpsFix ?: return@collect
                maybeRefetch(fix.lat, fix.lon)
            }
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
    }
}
