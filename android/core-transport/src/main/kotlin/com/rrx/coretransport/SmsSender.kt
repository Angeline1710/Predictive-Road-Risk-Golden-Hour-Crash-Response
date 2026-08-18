package com.rrx.coretransport

import android.Manifest
import android.app.Activity
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.telephony.SmsManager
import androidx.core.content.ContextCompat
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

/**
 * Sends an already-encoded RRX1 message (see [Rrx1Codec]) via the
 * platform SMS stack -- PRD.md §12.1's zero-data-connectivity delivery
 * path. Waits for the radio's own send confirmation (the standard
 * `sentIntent` broadcast pattern) rather than firing and forgetting, so
 * the channel-strategy layer above knows whether SMS actually left the
 * device, not just whether the API call was made.
 */
class SmsSender(private val context: Context) {

    val hasPermission: Boolean
        get() = ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS) ==
            PackageManager.PERMISSION_GRANTED

    /** @return true once every part of the (possibly multi-part) message
     * has been handed off to the radio successfully. */
    suspend fun send(destinationAddress: String, message: String): Boolean {
        if (!hasPermission) return false
        val smsManager = smsManager()
        val parts = smsManager.divideMessage(message)
        val action = "com.rrx.coretransport.SMS_SENT.${System.nanoTime()}"

        return suspendCancellableCoroutine { cont ->
            var remaining = parts.size
            var allOk = true

            val receiver = object : BroadcastReceiver() {
                override fun onReceive(receiverContext: Context, intent: Intent) {
                    if (resultCode != Activity.RESULT_OK) allOk = false
                    remaining--
                    if (remaining <= 0) {
                        runCatching { context.unregisterReceiver(this) }
                        if (cont.isActive) cont.resume(allOk)
                    }
                }
            }
            ContextCompat.registerReceiver(context, receiver, IntentFilter(action), ContextCompat.RECEIVER_NOT_EXPORTED)

            val sentIntent = PendingIntent.getBroadcast(
                context, 0, Intent(action).setPackage(context.packageName),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
            )
            val sentIntents = ArrayList<PendingIntent>(parts.size).apply { repeat(parts.size) { add(sentIntent) } }

            cont.invokeOnCancellation { runCatching { context.unregisterReceiver(receiver) } }

            smsManager.sendMultipartTextMessage(destinationAddress, null, parts, sentIntents, null)
        }
    }

    @Suppress("DEPRECATION")
    private fun smsManager(): SmsManager =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            context.getSystemService(SmsManager::class.java)
        } else {
            SmsManager.getDefault()
        }
}
