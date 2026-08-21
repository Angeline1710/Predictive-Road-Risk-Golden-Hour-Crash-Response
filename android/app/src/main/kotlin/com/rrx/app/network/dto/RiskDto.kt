package com.rrx.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Mirrors backend/app/api/risk.py's RiskContextOut field-for-field -- same
// "wire contract, not a guess" discipline as DeviceDto.kt.
@Serializable
data class RiskContextDto(
    @SerialName("segment_id") val segmentId: Int,
    val district: String? = null,
    @SerialName("road_class") val roadClass: String? = null,
    val score: Double,
    // "Low" | "Moderate" | "High" | "Severe" -- capitalized, per
    // backend/app/ml/risk_model.py's band_for(). Parsed by RiskBand.fromApi(),
    // not compared against directly, the same defensive pattern
    // web/src/lib/bands.ts's bandKeyFromApi() uses.
    val band: String,
    @SerialName("top_factors") val topFactors: List<String> = emptyList(),
    @SerialName("model_version") val modelVersion: String,
    // GeoJSON LineString coordinates, [lon, lat] pairs in order.
    val geometry: List<List<Double>>,
)
