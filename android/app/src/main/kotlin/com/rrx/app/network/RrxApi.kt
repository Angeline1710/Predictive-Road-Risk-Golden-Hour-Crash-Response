package com.rrx.app.network

import com.rrx.app.network.dto.DeviceRegisterRequest
import com.rrx.app.network.dto.DeviceRegisterResponse
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * One real endpoint, on purpose: this scaffold's job (task #18,
 * MVP-PLAN.md §3.3) is proving the toolchain and the DTO contract against
 * the live backend, not reimplementing core-transport's real channel
 * strategy (HTTPS + SMS fallback + retry). `POST /devices/register` is
 * the natural first call in the app's real lifecycle (PRD.md §10.1) and
 * needs no auth token to invoke, unlike everything else the API exposes.
 */
interface RrxApi {
    @POST("v1/devices/register")
    suspend fun registerDevice(@Body body: DeviceRegisterRequest): DeviceRegisterResponse
}
