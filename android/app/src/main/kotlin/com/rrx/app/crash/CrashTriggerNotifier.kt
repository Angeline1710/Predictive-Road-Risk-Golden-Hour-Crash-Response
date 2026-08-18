package com.rrx.app.crash

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import androidx.core.app.NotificationCompat
import com.rrx.coredetection.CrashPrediction
import com.rrx.coredetection.IncidentSeverity
import com.rrx.coresensing.DriveSessionState
import java.time.OffsetDateTime
import java.util.UUID

/**
 * Turns a [CrashPrediction] that has crossed the model's own decision
 * threshold into UX-APPFLOW.md §15's countdown screen. Lives in `app`,
 * not core-detection, for the same reason [com.rrx.app.ui.drive.DriveViewModel]
 * does the classification call itself: core-detection and core-sensing
 * stay mutually unaware of each other, and only `app` depends on both.
 *
 * [com.rrx.app.ui.drive.DriveViewModel] runs from a ViewModel backing a
 * foreground service's data, i.e. effectively a background context -- it
 * cannot call `startActivity()` directly, since Android 10+ blocks
 * background activity starts outright. A full-screen-intent notification
 * is the sanctioned way around that. On API 34+, `USE_FULL_SCREEN_INTENT`
 * additionally needs an explicit user grant via Settings (PRD.md §12.1);
 * when it isn't granted, the platform itself downgrades
 * `setFullScreenIntent` to a normal heads-up notification rather than
 * launching automatically -- there is no separate fallback path to write
 * here, since attempting `startActivity()` ourselves would hit the exact
 * background-start restriction this mechanism exists to bypass.
 */
object CrashTriggerNotifier {

    /** ml/reports/crash_detection_results.json: degraded/fusion/threshold,
     * the exact value the model was evaluated against. */
    const val P_CRASH_THRESHOLD = 0.29719674587249756f

    private const val CHANNEL_ID = "crash_trigger"
    private const val NOTIFICATION_ID = 4202

    /** No-op below threshold, or while a GPS fix isn't available yet --
     * [CrashTriggerParams] needs real coordinates, and a window without a
     * fix is also a window StageAGate's degraded arm may not even have
     * evaluated speed for. */
    fun maybeTrigger(context: Context, sensing: DriveSessionState.Sensing, prediction: CrashPrediction) {
        if (prediction.pCrash < P_CRASH_THRESHOLD) return
        val gpsFix = sensing.gpsFix ?: return
        notify(context, buildParams(sensing, gpsFix, prediction))
    }

    private fun buildParams(
        sensing: DriveSessionState.Sensing,
        gpsFix: com.rrx.coresensing.GpsFix,
        prediction: CrashPrediction,
    ): CrashTriggerParams = CrashTriggerParams(
        alertUuid = UUID.randomUUID().toString(),
        occurredAtIso = OffsetDateTime.now().toString(),
        // pCrash crossing the threshold and the severity head landing on
        // NONE are independent outputs of the same model and can disagree
        // in principle; NONE would leave totalSecondsFor() and the alert
        // payload with no real severity to describe a crash that was just
        // flagged as one, so this treats that combination as MODERATE
        // rather than propagating a contradiction into the countdown.
        severity = prediction.severity.takeIf { it != IncidentSeverity.NONE } ?: IncidentSeverity.MODERATE,
        pCrash = prediction.pCrash,
        peakAccelG = sensing.peakAccelG,
        lat = gpsFix.lat,
        lon = gpsFix.lon,
        accuracyM = gpsFix.accuracyM,
        headingDeg = gpsFix.headingDeg,
        speedKmh = gpsFix.speedKmh,
    )

    private fun notify(context: Context, params: CrashTriggerParams) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Crash detected", NotificationManager.IMPORTANCE_HIGH).apply {
                enableVibration(true)
                setBypassDnd(true)
            }
        )

        val intent = CrashCountdownActivity.intentFor(context, params)
        val pendingIntent = PendingIntent.getActivity(
            context,
            params.alertUuid.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle("Possible crash detected")
            .setContentText("Opening the alert countdown… tap if it doesn't open automatically")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true)
            .build()

        manager.notify(NOTIFICATION_ID, notification)
    }
}
