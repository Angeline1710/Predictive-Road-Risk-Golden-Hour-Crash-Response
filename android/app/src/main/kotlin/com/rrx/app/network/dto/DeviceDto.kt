package com.rrx.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Mirrors backend/app/schemas/device.py field-for-field -- this is the
// wire contract, not a guess at it. Keep in sync by hand, same practice as
// web/src/lib/api.ts.

@Serializable
data class DeviceRegisterRequest(
    @SerialName("device_hash") val deviceHash: String,
    val model: String? = null,
    @SerialName("android_version") val androidVersion: String? = null,
    @SerialName("app_version") val appVersion: String? = null,
    val locale: String = "en-IN",
)

@Serializable
data class TokenPairDto(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in_s") val expiresInS: Int,
)

@Serializable
data class DeviceRegisterResponse(
    @SerialName("device_id") val deviceId: String,
    val tokens: TokenPairDto,
)
