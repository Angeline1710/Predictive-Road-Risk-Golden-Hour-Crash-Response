package com.rrx.coresensing

import com.rrx.coresensing.SensingConfig.GPS_LEN

/**
 * The 12-second (1 Hz) GPS speed trace ml/crash_detection/model.py's `gps`
 * input expects -- 8 s pre-impact, 4 s post (GPS_IMPACT_IDX = 8). Pure
 * Kotlin so it's unit-testable without a location fix.
 */
class GpsSpeedBuffer(private val capacity: Int = GPS_LEN) {

    private val buffer = ArrayDeque<Float>(capacity)

    @Synchronized
    fun push(speedKmh: Float) {
        if (buffer.size == capacity) buffer.removeFirst()
        buffer.addLast(speedKmh)
    }

    @Synchronized
    fun latestOrNull(): Float? = buffer.lastOrNull()

    /** Null until the buffer has a full [GPS_LEN]-sample window. */
    @Synchronized
    fun snapshotWindow(): FloatArray? {
        if (buffer.size < capacity) return null
        return buffer.toFloatArray()
    }

    @Synchronized
    fun clear() = buffer.clear()
}
