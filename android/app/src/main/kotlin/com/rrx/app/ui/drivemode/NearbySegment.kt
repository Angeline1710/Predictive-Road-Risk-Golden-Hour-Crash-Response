package com.rrx.app.ui.drivemode

import com.rrx.app.network.dto.RiskContextDto
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/** A [RiskContextDto] plus its distance from the driver right now --
 * [DriveModeViewModel] recomputes this list on every GPS fix, not the raw
 * DTO list, since "nearby" only means something relative to a position. */
data class NearbySegment(val risk: RiskContextDto, val distanceM: Double, val band: RiskBand)

/**
 * Distance from ([lat],[lon]) to the *nearest vertex* of [geometry] ([lon,
 * lat] pairs), not a true point-to-segment projection along the polyline.
 * A real "distance ahead along the route" needs `/risk/route` (PRD.md §10.2
 * lists it as **not implemented** server-side) or client-side map-matching
 * neither of which this pass builds -- nearest-vertex is a documented
 * proxy, good enough to sort "what's nearby" but not to claim an exact
 * "2.1 km ahead" the way UX-APPFLOW.md §13's mock shows.
 */
fun distanceToNearestVertexM(lat: Double, lon: Double, geometry: List<List<Double>>): Double =
    geometry.minOfOrNull { (vLon, vLat) -> haversineM(lat, lon, vLat, vLon) } ?: Double.MAX_VALUE

private const val EARTH_RADIUS_M = 6_371_000.0

private fun haversineM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = sin(dLat / 2) * sin(dLat / 2) +
        cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
    return EARTH_RADIUS_M * 2 * atan2(sqrt(a), sqrt(1 - a))
}
