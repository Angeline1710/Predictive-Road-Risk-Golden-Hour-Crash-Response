package com.rrx.coresensing

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ImuRingBufferTest {

    private fun sample(ax: Float, ay: Float, az: Float, gx: Float = 0f, gy: Float = 0f, gz: Float = 0f) =
        ImuSample(ax, ay, az, gx, gy, gz, timestampNs = 0L)

    @Test
    fun `null until the window is full`() {
        val buf = ImuRingBuffer(capacity = 4)
        repeat(3) { buf.push(sample(0f, 0f, 1f), accelRailG = 8f) }
        assertNull(buf.snapshotWindow())
        buf.push(sample(0f, 0f, 1f), accelRailG = 8f)
        assertEquals(4, buf.snapshotWindow()!!.size)
    }

    @Test
    fun `column order is accel, gyro, clip-mask -- matches build_dataset's concatenate order`() {
        val buf = ImuRingBuffer(capacity = 1)
        // Below rail: no clipping expected.
        buf.push(sample(ax = 1f, ay = 2f, az = 3f, gx = 10f, gy = 20f, gz = 30f), accelRailG = 8f)
        val row = buf.snapshotWindow()!!.single()
        assertArrayEquals(
            floatArrayOf(1f, 2f, 3f, 10f, 20f, 30f, 0f, 0f, 0f),
            row,
            1e-6f,
        )
    }

    @Test
    fun `clip mask fires per-axis at the rail, and the value itself is clamped`() {
        val buf = ImuRingBuffer(capacity = 1)
        buf.push(sample(ax = 9f, ay = -9f, az = 2f), accelRailG = 8f)
        val row = buf.snapshotWindow()!!.single()
        // ax, ay clamped to +/-8; az untouched.
        assertArrayEquals(floatArrayOf(8f, -8f, 2f), row.copyOfRange(0, 3), 1e-6f)
        // clip mask: x and y clipped, z not.
        assertArrayEquals(floatArrayOf(1f, 1f, 0f), row.copyOfRange(6, 9), 1e-6f)
    }

    @Test
    fun `gyro is clamped to the rail independently of accel`() {
        val buf = ImuRingBuffer(capacity = 1)
        buf.push(sample(ax = 0f, ay = 0f, az = 1f, gx = 5000f, gy = -5000f, gz = 0f), accelRailG = 8f)
        val row = buf.snapshotWindow()!!.single()
        assertArrayEquals(
            floatArrayOf(SensingConfig.GYRO_RAIL_DPS, -SensingConfig.GYRO_RAIL_DPS, 0f),
            row.copyOfRange(3, 6),
            1e-6f,
        )
    }

    @Test
    fun `oldest sample drops once the buffer is full`() {
        val buf = ImuRingBuffer(capacity = 2)
        buf.push(sample(1f, 0f, 0f), accelRailG = 8f)
        buf.push(sample(2f, 0f, 0f), accelRailG = 8f)
        buf.push(sample(3f, 0f, 0f), accelRailG = 8f)
        val window = buf.snapshotWindow()!!
        assertEquals(2f, window[0][0], 1e-6f)
        assertEquals(3f, window[1][0], 1e-6f)
    }

    @Test
    fun `peak accel magnitude is the euclidean norm across the buffer`() {
        val buf = ImuRingBuffer(capacity = 3)
        buf.push(sample(1f, 0f, 0f), accelRailG = 8f)
        buf.push(sample(3f, 4f, 0f), accelRailG = 8f) // magnitude 5
        buf.push(sample(0f, 0f, 2f), accelRailG = 8f)
        assertEquals(5f, buf.peakAccelMagnitudeG(), 1e-5f)
    }
}
