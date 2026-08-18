package com.rrx.coretransport

import com.rrx.coretransport.dto.AlertCreateDto
import com.rrx.coretransport.dto.AlertResponseDto
import retrofit2.http.Body
import retrofit2.http.POST

/** `POST /v1/alerts` -- backend/app/api/alerts.py's `create_alert`. */
interface AlertApi {
    @POST("v1/alerts")
    suspend fun createAlert(@Body body: AlertCreateDto): AlertResponseDto
}
