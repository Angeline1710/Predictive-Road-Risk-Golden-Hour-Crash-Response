package com.rrx.app.ui.drivemode

/** UX-APPFLOW.md §14: fired once per qualifying segment entry (gated by
 * FR-4.2 band, FR-4.4's 15-minute per-segment cooldown, and FR-4.5's
 * 25 km/h speed floor -- all enforced in [DriveModeViewModel]). Consumed
 * by [DriveModeScreen] to fire the one-shot voice line and, for Severe,
 * the double haptic pulse. */
data class RiskWarningEvent(val segmentId: Int, val band: RiskBand, val topFactors: List<String>)

/** The Severe overlay's live state. `distanceM` updates every frame while
 * the driver stays in the triggering segment -- nearest-vertex distance,
 * the same documented proxy [NearbySegment]/Segment Ribbon use, not a
 * true distance-ahead-along-the-route (see `distanceToNearestVertexM`'s
 * doc comment). Cleared by [DriveModeViewModel] the instant the driver is
 * no longer nearest to this segment or its band drops below Severe --
 * "Auto-dismisses on exiting the segment" (UX-APPFLOW.md §14). */
data class SevereOverlayState(val segmentId: Int, val topFactors: List<String>, val distanceM: Double)
