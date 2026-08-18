package com.rrx.coresensing

/**
 * A full location fix -- [GpsSpeedSource] previously discarded everything
 * but speed, which is fine for [GpsSpeedBuffer]/[StageAGate] but leaves no
 * way to actually report *where* a crash happened. A real alert payload
 * needs lat/lon regardless of what triggered it.
 */
data class GpsFix(
    val lat: Double,
    val lon: Double,
    val accuracyM: Float,
    val headingDeg: Float,
    val speedKmh: Float,
)
