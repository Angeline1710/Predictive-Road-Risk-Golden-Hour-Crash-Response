package com.rrx.coresensing

import android.Manifest
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.android.gms.location.ActivityRecognition
import com.google.android.gms.location.ActivityTransition
import com.google.android.gms.location.ActivityTransitionRequest
import com.google.android.gms.location.ActivityTransitionResult
import com.google.android.gms.location.DetectedActivity

/**
 * PRD.md §12.1: Activity Recognition gates sensing to actual driving --
 * "the single biggest battery win." Registers for IN_VEHICLE enter/exit
 * transitions and calls back when either fires.
 *
 * Scope note: this only reacts while [start] has been called (i.e. while
 * [DriveSensingService] is already running), auto-stopping it on EXIT.
 * True hands-off "detect driving and start sensing with the app not even
 * open" needs a BOOT_COMPLETED receiver plus an always-on transition
 * subscription independent of this service -- MVP-PLAN.md §3.3 lists
 * "Stage-A gate + drive-session lifecycle" as its own line item, and that
 * always-on piece is the remainder of it, not built here.
 */
class DrivingDetector(private val context: Context) {

    private val client = ActivityRecognition.getClient(context)
    private var receiver: BroadcastReceiver? = null
    private var pendingIntent: PendingIntent? = null

    val hasPermission: Boolean
        get() = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ActivityCompat.checkSelfPermission(context, Manifest.permission.ACTIVITY_RECOGNITION) ==
                PackageManager.PERMISSION_GRANTED
        } else {
            true // ACTIVITY_RECOGNITION is a normal (auto-granted) permission before API 29
        }

    fun start(onVehicleStateChanged: (inVehicle: Boolean) -> Unit) {
        if (!hasPermission) return

        val receiverInstance = object : BroadcastReceiver() {
            override fun onReceive(receiverContext: Context, intent: Intent) {
                if (!ActivityTransitionResult.hasResult(intent)) return
                val result = ActivityTransitionResult.extractResult(intent) ?: return
                for (event in result.transitionEvents) {
                    if (event.activityType != DetectedActivity.IN_VEHICLE) continue
                    onVehicleStateChanged(event.transitionType == ActivityTransition.ACTIVITY_TRANSITION_ENTER)
                }
            }
        }
        ContextCompat.registerReceiver(
            context, receiverInstance, IntentFilter(TRANSITION_ACTION), ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        receiver = receiverInstance

        val intent = Intent(TRANSITION_ACTION).setPackage(context.packageName)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
        val pi = PendingIntent.getBroadcast(context, 0, intent, flags)
        pendingIntent = pi

        val request = ActivityTransitionRequest(
            listOf(
                ActivityTransition.Builder()
                    .setActivityType(DetectedActivity.IN_VEHICLE)
                    .setActivityTransition(ActivityTransition.ACTIVITY_TRANSITION_ENTER)
                    .build(),
                ActivityTransition.Builder()
                    .setActivityType(DetectedActivity.IN_VEHICLE)
                    .setActivityTransition(ActivityTransition.ACTIVITY_TRANSITION_EXIT)
                    .build(),
            )
        )
        client.requestActivityTransitionUpdates(request, pi)
    }

    fun stop() {
        pendingIntent?.let { client.removeActivityTransitionUpdates(it) }
        receiver?.let { context.unregisterReceiver(it) }
        receiver = null
        pendingIntent = null
    }

    private companion object {
        const val TRANSITION_ACTION = "com.rrx.coresensing.ACTIVITY_TRANSITION"
    }
}
