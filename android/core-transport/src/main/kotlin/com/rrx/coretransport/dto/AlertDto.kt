package com.rrx.coretransport.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Mirrors backend/app/schemas/alert.py field-for-field -- the wire
// contract, not a guess at it. Same practice as app/network/dto/DeviceDto.kt
// and web/src/lib/api.ts. `occurred_at` is a String here (ISO-8601 with
// offset, e.g. from java.time.OffsetDateTime.toString()) rather than a
// typed date -- kotlinx.serialization has no built-in java.time support
// without an extra module, and the backend's own field_validator only
// requires the string be timezone-aware, not any particular Kotlin type.

@Serializable
data class LocationDto(
    val lat: Double,
    val lon: Double,
    @SerialName("accuracy_m") val accuracyM: Double,
    @SerialName("altitude_m") val altitudeM: Double? = null,
)

@Serializable
data class MotionDto(
    @SerialName("speed_kmh") val speedKmh: Double,
    @SerialName("heading_deg") val headingDeg: Double,
    @SerialName("peak_g") val peakG: Double,
    @SerialName("delta_v_kmh") val deltaVKmh: Double? = null,
    @SerialName("impact_direction") val impactDirection: String? = null,
    val rollover: Boolean = false,
    @SerialName("still_moving") val stillMoving: Boolean? = null,
)

@Serializable
data class DetectionDto(
    @SerialName("p_crash") val pCrash: Double,
    val severity: String,
    @SerialName("model_version") val modelVersion: String,
)

@Serializable
data class WindowDto(
    @SerialName("duration_s") val durationS: Int,
    val outcome: String,
)

@Serializable
data class DeviceContextDto(
    @SerialName("battery_pct") val batteryPct: Int? = null,
    val locale: String = "en-IN",
    @SerialName("app_version") val appVersion: String? = null,
)

@Serializable
data class AlertCreateDto(
    @SerialName("alert_uuid") val alertUuid: String,
    @SerialName("device_id") val deviceId: String? = null,
    @SerialName("occurred_at") val occurredAt: String,
    val location: LocationDto,
    val motion: MotionDto,
    val detection: DetectionDto,
    val window: WindowDto,
    @SerialName("device_context") val deviceContext: DeviceContextDto = DeviceContextDto(),
    @SerialName("occupant_hint") val occupantHint: Int? = null,
    @SerialName("is_simulated") val isSimulated: Boolean = false,
)

@Serializable
data class RiskContextDto(
    val score: Double,
    val band: String,
    @SerialName("top_factors") val topFactors: List<String> = emptyList(),
)

@Serializable
data class DispatchInfoDto(
    val gateway: String,
    @SerialName("is_simulated") val isSimulated: Boolean,
    @SerialName("ticket_id") val ticketId: String? = null,
    @SerialName("eta_note") val etaNote: String? = null,
)

@Serializable
data class NearestUnitDto(
    val id: Long,
    val name: String,
    val kind: String,
    @SerialName("distance_km") val distanceKm: Double,
)

@Serializable
data class AlertResponseDto(
    @SerialName("alert_uuid") val alertUuid: String,
    val status: String,
    @SerialName("segment_id") val segmentId: Long? = null,
    val landmark: String? = null,
    @SerialName("risk_context") val riskContext: RiskContextDto? = null,
    val dispatch: DispatchInfoDto? = null,
    @SerialName("nearest_units") val nearestUnits: List<NearestUnitDto> = emptyList(),
)
