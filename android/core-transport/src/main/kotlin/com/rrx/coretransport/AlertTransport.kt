package com.rrx.coretransport

import android.content.Context
import com.rrx.coretransport.dto.AlertCreateDto
import com.rrx.coretransport.dto.AlertResponseDto
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withTimeoutOrNull
import java.time.OffsetDateTime
import java.util.UUID

/** What actually happened when [AlertTransport.send] tried to deliver an
 * alert -- both fields can be non-null on CRITICAL severity, where both
 * channels fire in parallel. */
data class TransportResult(
    val httpsResponse: AlertResponseDto?,
    val smsSent: Boolean?,
) {
    val delivered: Boolean get() = httpsResponse != null || smsSent == true
}

/**
 * PRD.md §6.2's connectivity-layer channel strategy: try HTTPS (6s
 * deadline), and on CRITICAL severity fire SMS in parallel rather than
 * only after HTTPS fails ("Channels 1 and 2 are not exclusive"). If HTTPS
 * doesn't succeed in the immediate attempt, enqueues [AlertSendWorker] so
 * the full payload (including the sensor trace SMS can't carry) still
 * lands eventually -- "retries the full payload upload for up to 24h so
 * the sensor trace eventually lands even if only the SMS got through in
 * the moment."
 *
 * Channel 3 ("Local escalation": siren, emergency-contact SMS, one-tap
 * call-112) is a UI/notification concern, not a network transport one --
 * out of scope here, tracked with the cancel-window screen in
 * MVP-PLAN.md §3.3.
 */
class AlertTransport(
    private val context: Context,
    private val alertApi: AlertApi,
    private val smsSender: SmsSender,
    private val baseUrl: String,
    /** The SMS gateway/companion-phone number this build sends RRX1
     * messages to -- see android/README.md for why this is a placeholder
     * needing real configuration, same open item as MVP-PLAN.md §2②'s
     * companion-phone receiver. */
    private val smsDestination: String,
) {
    suspend fun send(payload: AlertCreateDto): TransportResult {
        val severity = payload.detection.severity
        val result = if (severity == "CRITICAL") {
            coroutineScope {
                val https = async { attemptHttps(payload) }
                val sms = async { attemptSms(payload) }
                TransportResult(https.await(), sms.await())
            }
        } else {
            val https = attemptHttps(payload)
            if (https != null) {
                TransportResult(https, null)
            } else {
                TransportResult(null, attemptSms(payload))
            }
        }

        if (result.httpsResponse == null) {
            AlertSendWorker.enqueue(context, baseUrl, payload)
        }
        return result
    }

    // Never throws past here -- a transport failure degrades the result,
    // it does not propagate, mirroring backend/app/services/alerts.py's
    // "must degrade, never raise past here" posture on the send side too.
    private suspend fun attemptHttps(payload: AlertCreateDto): AlertResponseDto? =
        try {
            withTimeoutOrNull(HTTPS_DEADLINE_MS) { alertApi.createAlert(payload) }
        } catch (e: Exception) {
            null
        }

    private suspend fun attemptSms(payload: AlertCreateDto): Boolean =
        try {
            withTimeoutOrNull(SMS_DEADLINE_MS) { smsSender.send(smsDestination, buildRrx1Message(payload)) } ?: false
        } catch (e: Exception) {
            false
        }

    private fun buildRrx1Message(payload: AlertCreateDto): String =
        Rrx1Codec.encode(
            alertUuid = UUID.fromString(payload.alertUuid),
            lat = payload.location.lat,
            lon = payload.location.lon,
            occurredAtEpochSeconds = OffsetDateTime.parse(payload.occurredAt).toEpochSecond(),
            severity = payload.detection.severity,
            speedKmh = payload.motion.speedKmh,
            headingDeg = payload.motion.headingDeg,
            gpsAccuracyM = payload.location.accuracyM,
            peakG = payload.motion.peakG,
            rollover = payload.motion.rollover,
            stillMoving = payload.motion.stillMoving ?: false,
            // AlertCreateDto has no field for "the user was unresponsive during
            // the cancel window" distinct from "the window simply expired" --
            // the HTTPS schema's window.outcome only has EXPIRED/CANCELLED, no
            // separate unresponsive signal. Rather than guess, this is always
            // false until the cancel-window screen (unbuilt) actually tracks
            // that distinction.
            unresponsive = false,
            cancelWindowExpired = payload.window.outcome == "EXPIRED",
        )

    companion object {
        // PRD.md §6.2's per-channel deadlines.
        private const val HTTPS_DEADLINE_MS = 6_000L
        private const val SMS_DEADLINE_MS = 15_000L
    }
}
