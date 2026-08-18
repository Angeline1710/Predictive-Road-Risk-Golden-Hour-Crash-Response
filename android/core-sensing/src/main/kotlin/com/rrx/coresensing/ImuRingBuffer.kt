package com.rrx.coresensing

import com.rrx.coresensing.SensingConfig.WIN_LEN
import kotlin.math.abs

/**
 * Circular buffer holding the last [WIN_LEN] IMU samples and producing the
 * exact (200, 9) tensor layout `ml/crash_detection/build_dataset.py` builds:
 * `np.concatenate([a_obs, g_obs, clip], axis=1)` -- accel xyz, gyro xyz,
 * per-axis clip mask xyz, in that column order. Getting this order wrong
 * would silently feed the trained model a scrambled input; there is no
 * error the framework can raise for that, which is exactly why this class
 * has a unit test asserting the column layout directly rather than trusting
 * the concatenation order by inspection.
 *
 * Pure Kotlin, no Android dependency -- the clip rail is passed in by the
 * caller (ImuSensorSource, which reads it from the real hardware sensor's
 * `getMaximumRange()`), so this class is fully unit-testable on the JVM.
 */
class ImuRingBuffer(private val capacity: Int = WIN_LEN) {

    private val buffer = ArrayDeque<FloatArray>(capacity)

    val size: Int
        @Synchronized get() = buffer.size

    /**
     * @param accelRailG the accelerometer's hardware saturation point, in g
     *   -- see ImuSensorSource for how this is derived from
     *   `Sensor.getMaximumRange()`. Approximates the clip mask against
     *   TYPE_LINEAR_ACCELERATION's magnitude rather than the raw
     *   (gravity-included) accelerometer, which is the best available
     *   proxy without replicating Android's own sensor-fusion gravity
     *   removal -- see android/README.md for why that's a known gap, not
     *   an oversight.
     */
    @Synchronized
    fun push(sample: ImuSample, accelRailG: Float, gyroRailDps: Float = SensingConfig.GYRO_RAIL_DPS) {
        val clipX = if (abs(sample.accelXG) >= accelRailG) 1f else 0f
        val clipY = if (abs(sample.accelYG) >= accelRailG) 1f else 0f
        val clipZ = if (abs(sample.accelZG) >= accelRailG) 1f else 0f

        val gx = sample.gyroXDps.coerceIn(-gyroRailDps, gyroRailDps)
        val gy = sample.gyroYDps.coerceIn(-gyroRailDps, gyroRailDps)
        val gz = sample.gyroZDps.coerceIn(-gyroRailDps, gyroRailDps)

        val row = floatArrayOf(
            sample.accelXG.coerceIn(-accelRailG, accelRailG),
            sample.accelYG.coerceIn(-accelRailG, accelRailG),
            sample.accelZG.coerceIn(-accelRailG, accelRailG),
            gx, gy, gz,
            clipX, clipY, clipZ,
        )

        if (buffer.size == capacity) buffer.removeFirst()
        buffer.addLast(row)
    }

    /** Null until the buffer has a full [WIN_LEN]-sample window. */
    @Synchronized
    fun snapshotWindow(): Array<FloatArray>? {
        if (buffer.size < capacity) return null
        return buffer.toTypedArray()
    }

    /** Peak |acceleration| (Euclidean norm across the 3 accel axes) in the
     * buffer's current contents -- what StageAGate evaluates against. */
    @Synchronized
    fun peakAccelMagnitudeG(): Float {
        var peak = 0f
        for (row in buffer) {
            val mag = kotlin.math.sqrt(row[0] * row[0] + row[1] * row[1] + row[2] * row[2])
            if (mag > peak) peak = mag
        }
        return peak
    }

    @Synchronized
    fun clear() = buffer.clear()
}
