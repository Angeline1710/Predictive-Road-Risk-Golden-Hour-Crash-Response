package com.rrx.app.network

import com.rrx.app.network.dto.DeviceRegisterRequest
import com.rrx.app.network.dto.DeviceRegisterResponse
import com.rrx.app.network.dto.RiskContextDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * `POST /devices/register` is the natural first call in the app's real
 * lifecycle (PRD.md §10.1) and needs no auth token to invoke, unlike
 * everything else the API exposes. `GET /risk/bbox` is Drive Mode's
 * (UX-APPFLOW.md §13) live risk-banded map data -- the same endpoint
 * `web/src/lib/api.ts` calls for the dashboard's Live Operations map,
 * so this is the second client, not a second implementation, of that
 * contract.
 */
interface RrxApi {
    @POST("v1/devices/register")
    suspend fun registerDevice(@Body body: DeviceRegisterRequest): DeviceRegisterResponse

    @GET("v1/risk/bbox")
    suspend fun riskBbox(
        @Query("minlat") minLat: Double,
        @Query("minlon") minLon: Double,
        @Query("maxlat") maxLat: Double,
        @Query("maxlon") maxLon: Double,
        @Query("limit") limit: Int = 200,
    ): List<RiskContextDto>
}
