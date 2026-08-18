package com.rrx.coresensing

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.isActive
import kotlinx.coroutines.delay

/**
 * Foreground service tying [ImuSensorSource], [GpsSpeedSource], and
 * [DrivingDetector] together, per PRD.md §12.1's "Foreground Service +
 * WorkManager ... the only reliable way to run continuous sensing on
 * modern Android." Publishes live state via [DriveSensingBus] rather than
 * a bound-service interface -- see that file's doc comment for why.
 *
 * What this does NOT do yet: invoke the (unbuilt) TFLite classifier when
 * Stage-A fires, or do anything with a confirmed crash. That's
 * core-detection and the cancel-window screen -- MVP-PLAN.md §3.3 tracks
 * both as separate, unbuilt line items. This service's job stops at
 * "here is a live Stage-A decision," which is exactly as far as PRD
 * §6.1.2 scopes it.
 */
class DriveSensingService : LifecycleService() {

    private lateinit var imuBuffer: ImuRingBuffer
    private lateinit var gpsBuffer: GpsSpeedBuffer
    private lateinit var imuSource: ImuSensorSource
    private lateinit var gpsSource: GpsSpeedSource
    private lateinit var drivingDetector: DrivingDetector
    private var evaluationLoop: Job? = null
    private var isRunning = false

    override fun onCreate() {
        super.onCreate()
        imuBuffer = ImuRingBuffer()
        gpsBuffer = GpsSpeedBuffer()
        imuSource = ImuSensorSource(this, imuBuffer)
        gpsSource = GpsSpeedSource(this, gpsBuffer)
        drivingDetector = DrivingDetector(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        if (isRunning) return START_STICKY

        if (!imuSource.available) {
            DriveSensingBus.publish(DriveSessionState.Unavailable("Missing linear-accelerometer or gyroscope"))
            stopSelf()
            return START_NOT_STICKY
        }
        isRunning = true

        startForegroundCompat()
        imuSource.start()
        gpsSource.start()
        drivingDetector.start { inVehicle ->
            if (!inVehicle) stopSelf() // exited the vehicle -- the battery win PRD §12.1 calls out
        }

        evaluationLoop = lifecycleScope.launch {
            DriveSensingBus.publish(DriveSessionState.WarmingUp)
            while (isActive) {
                val imuWindow = imuBuffer.snapshotWindow()
                if (imuWindow != null) {
                    val peak = imuBuffer.peakAccelMagnitudeG()
                    val speed = gpsSource.currentSpeedKmhOrNull()
                    DriveSensingBus.publish(
                        DriveSessionState.Sensing(
                            peakAccelG = peak,
                            speedKmh = speed,
                            stageA = StageAGate.evaluate(peak, speed),
                            imuWindow = imuWindow,
                            gpsWindow = gpsBuffer.snapshotWindow(),
                            accelRailG = imuSource.accelRailG,
                        )
                    )
                }
                delay(EVALUATION_INTERVAL_MS)
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        isRunning = false
        evaluationLoop?.cancel()
        imuSource.stop()
        gpsSource.stop()
        drivingDetector.stop()
        DriveSensingBus.publish(DriveSessionState.Idle)
        super.onDestroy()
    }

    override fun onBind(intent: Intent) = super.onBind(intent) // LifecycleService supplies the binder

    /**
     * `Service.startForeground(int, Notification, int)` -- the overload
     * that takes a foreground-service type -- doesn't exist below API 29;
     * calling it unconditionally on minSdk 26 would throw
     * NoSuchMethodError at runtime on real API 26-28 devices, a failure
     * mode compiling against compileSdk 35 can't surface since the method
     * resolves fine at compile time. Must branch on the actual overload,
     * not just pass 0 as a type to the 3-arg one.
     */
    private fun startForegroundCompat() {
        val notification = buildNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildNotification(): Notification {
        // No API-level guard: minSdk 26 IS Build.VERSION_CODES.O, so
        // notification channels are unconditionally required here, not
        // merely supported.
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Drive sensing", NotificationManager.IMPORTANCE_LOW)
        )
        // UX-APPFLOW.md §13's ambient notification (risk band, live speed,
        // "Next: Severe in 2.1 km") needs the risk-serving pipeline wired
        // into the app, which isn't part of this scaffold -- plain text
        // for now, real content once core-transport/core-detection land.
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Road-Risk Response")
            .setContentText("Monitoring for crashes")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val NOTIFICATION_ID = 4201
        private const val CHANNEL_ID = "drive_sensing"
        private const val EVALUATION_INTERVAL_MS = 200L

        fun start(context: Context) {
            context.startForegroundService(Intent(context, DriveSensingService::class.java))
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, DriveSensingService::class.java))
        }
    }
}
