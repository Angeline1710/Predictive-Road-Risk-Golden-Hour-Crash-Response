package com.rrx.coresensing

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

/**
 * Wraps the real Android sensor stack and feeds an [ImuRingBuffer] at
 * [SensingConfig.IMU_HZ]. Reads TYPE_LINEAR_ACCELERATION for the accel
 * channels (gravity already removed by the platform's own sensor fusion --
 * the same physical quantity ml/crash_detection/imu_data.py trains on) and
 * TYPE_GYROSCOPE for the gyro channels, converting rad/s to deg/s to match
 * ml/common/config.py's convention.
 *
 * The clip-mask rail is read from the *raw* TYPE_ACCELEROMETER sensor's
 * `getMaximumRange()` -- that's the sensor that genuinely saturates in
 * hardware, whereas TYPE_LINEAR_ACCELERATION is a derived/fused signal
 * whose own reported range doesn't necessarily reflect the hardware rail.
 * This is a real approximation, not a perfect replica of
 * ml/crash_detection/sensors.py's synthetic clipping model, which clips
 * gravity-removed acceleration directly -- see android/README.md.
 */
class ImuSensorSource(
    context: Context,
    private val ringBuffer: ImuRingBuffer,
) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val linearAccel: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
    private val gyro: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
    private val rawAccelForRail: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    /** Exposed so a downstream classifier (core-detection) can feed the
     * exact same rail into its `sat_rail_g` feature -- see
     * ml/crash_detection/sensors.py's `saturation_features()`, which uses
     * the device's per-sample rail verbatim, not a re-derived constant. */
    val accelRailG: Float =
        (rawAccelForRail?.maximumRange ?: (16f * SI_G)) / SI_G
    private val gyroRailDps: Float =
        gyro?.maximumRange?.let { it * RAD2DEG } ?: SensingConfig.GYRO_RAIL_DPS

    // Gyro and accel arrive as separate events at slightly different
    // instants; each linear-accel tick is paired with the most recent
    // gyro reading rather than block-synchronised, which is adequate at
    // IMU_HZ but not sample-exact.
    @Volatile private var latestGyroDps = floatArrayOf(0f, 0f, 0f)

    val available: Boolean get() = linearAccel != null && gyro != null

    fun start() {
        if (!available) return
        sensorManager.registerListener(this, linearAccel, SAMPLING_PERIOD_US)
        sensorManager.registerListener(this, gyro, SAMPLING_PERIOD_US)
    }

    fun stop() {
        sensorManager.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_GYROSCOPE -> {
                latestGyroDps = floatArrayOf(
                    event.values[0] * RAD2DEG,
                    event.values[1] * RAD2DEG,
                    event.values[2] * RAD2DEG,
                )
            }
            Sensor.TYPE_LINEAR_ACCELERATION -> {
                val g = latestGyroDps
                ringBuffer.push(
                    ImuSample(
                        accelXG = event.values[0] / SI_G,
                        accelYG = event.values[1] / SI_G,
                        accelZG = event.values[2] / SI_G,
                        gyroXDps = g[0], gyroYDps = g[1], gyroZDps = g[2],
                        timestampNs = event.timestamp,
                    ),
                    accelRailG = accelRailG,
                    gyroRailDps = gyroRailDps,
                )
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private companion object {
        const val SI_G = 9.80665f
        const val RAD2DEG = 57.29577951308232f
        val SAMPLING_PERIOD_US = 1_000_000 / SensingConfig.IMU_HZ
    }
}
