package com.rrx.coresensing

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Looper
import android.os.SystemClock
import androidx.core.app.ActivityCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority

/**
 * Wraps FusedLocationProviderClient at [SensingConfig.GPS_HZ] and feeds a
 * [GpsSpeedBuffer]. `Location.speed` (m/s, GPS-derived ground speed) is
 * converted to km/h to match ml/common/config.py's units throughout.
 * Also tracks the latest full [GpsFix] -- StageAGate/TabularFeatures only
 * ever needed speed, but a real alert payload needs lat/lon too.
 */
class GpsSpeedSource(
    private val context: Context,
    private val speedBuffer: GpsSpeedBuffer,
) {
    private val fusedClient = LocationServices.getFusedLocationProviderClient(context)

    @Volatile private var latestFix: GpsFix? = null
    @Volatile private var lastFixElapsedRealtimeMs: Long = 0L

    private val callback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            val speedKmh = location.speed * 3.6f
            latestFix = GpsFix(
                lat = location.latitude,
                lon = location.longitude,
                accuracyM = location.accuracy,
                headingDeg = location.bearing,
                speedKmh = speedKmh,
            )
            lastFixElapsedRealtimeMs = SystemClock.elapsedRealtime()
            speedBuffer.push(speedKmh)
        }
    }

    val hasLocationPermission: Boolean
        get() = ActivityCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED

    fun start() {
        if (!hasLocationPermission) return
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, INTERVAL_MS)
            .setMinUpdateIntervalMillis(INTERVAL_MS)
            .build()
        fusedClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
    }

    fun stop() {
        fusedClient.removeLocationUpdates(callback)
    }

    /**
     * Null if there is no fix yet, or the last one is older than
     * [SensingConfig.GPS_FIX_STALE_MS] -- StageAGate treats a stale fix the
     * same as no fix, which is what makes its degraded arm actually
     * degraded rather than trusting a speed reading from minutes ago.
     */
    fun currentSpeedKmhOrNull(): Float? = currentFixOrNull()?.speedKmh

    /** Same staleness rule as [currentSpeedKmhOrNull], for callers that
     * need the full fix (lat/lon included) rather than just speed. */
    fun currentFixOrNull(): GpsFix? {
        val fix = latestFix ?: return null
        val age = SystemClock.elapsedRealtime() - lastFixElapsedRealtimeMs
        return if (age <= SensingConfig.GPS_FIX_STALE_MS) fix else null
    }

    private companion object {
        const val INTERVAL_MS = 1000L / SensingConfig.GPS_HZ
    }
}
