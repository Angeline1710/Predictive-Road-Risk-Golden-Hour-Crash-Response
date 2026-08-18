package com.rrx.coretransport

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkRequest
import androidx.work.WorkerParameters
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.rrx.coretransport.dto.AlertCreateDto
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

/**
 * PRD.md §6.2: "WorkManager with exponential backoff retries the full
 * payload upload for up to 24h so the sensor trace eventually lands even
 * if only the SMS got through in the moment." [AlertTransport] enqueues
 * this only when its own immediate HTTPS attempt didn't succeed.
 *
 * Builds its own minimal Retrofit/OkHttp/Json stack from a `baseUrl`
 * passed in via [Data] rather than sharing `app`'s Hilt-provided one --
 * WorkManager's default factory constructs `CoroutineWorker`s via a plain
 * `(Context, WorkerParameters)` reflection call, and wiring Hilt-Work
 * (a `HiltWorkerFactory` + `Configuration.Provider` in the Application
 * class) is a real app-wide structural change this pass didn't take on.
 * The duplication is a handful of lines, not a maintenance trap on the
 * scale of re-deriving RRX1's bit-packing.
 */
class AlertSendWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val baseUrl = inputData.getString(KEY_BASE_URL) ?: return Result.failure()
        val payloadJson = inputData.getString(KEY_PAYLOAD_JSON) ?: return Result.failure()
        val firstEnqueuedAtMs = inputData.getLong(KEY_FIRST_ENQUEUED_AT_MS, System.currentTimeMillis())

        if (System.currentTimeMillis() - firstEnqueuedAtMs > RETRY_WINDOW_MS) {
            return Result.failure()
        }

        val json = Json { ignoreUnknownKeys = true }
        return try {
            val payload = json.decodeFromString(AlertCreateDto.serializer(), payloadJson)
            val api = Retrofit.Builder()
                .baseUrl(baseUrl)
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                .build()
                .create(AlertApi::class.java)
            api.createAlert(payload)
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    companion object {
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_PAYLOAD_JSON = "payload_json"
        private const val KEY_FIRST_ENQUEUED_AT_MS = "first_enqueued_at_ms"
        private val RETRY_WINDOW_MS = TimeUnit.HOURS.toMillis(24)

        fun enqueue(context: Context, baseUrl: String, payload: AlertCreateDto) {
            val json = Json { ignoreUnknownKeys = true }
            val data = Data.Builder()
                .putString(KEY_BASE_URL, baseUrl)
                .putString(KEY_PAYLOAD_JSON, json.encodeToString(AlertCreateDto.serializer(), payload))
                .putLong(KEY_FIRST_ENQUEUED_AT_MS, System.currentTimeMillis())
                .build()
            val request = OneTimeWorkRequestBuilder<AlertSendWorker>()
                .setInputData(data)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, WorkRequest.MIN_BACKOFF_MILLIS, TimeUnit.MILLISECONDS)
                .addTag(payload.alertUuid)
                .build()
            // Idempotent per alert_uuid -- AlertTransport is the only caller,
            // and it's called at most once per confirmed crash, but this
            // guards against a duplicate enqueue from a retried caller
            // rather than silently double-sending.
            WorkManager.getInstance(context)
                .enqueueUniqueWork(payload.alertUuid, ExistingWorkPolicy.KEEP, request)
        }
    }
}
