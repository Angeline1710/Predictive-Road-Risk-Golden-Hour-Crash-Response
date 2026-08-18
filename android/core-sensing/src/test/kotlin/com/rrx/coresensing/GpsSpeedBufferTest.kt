package com.rrx.coresensing

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class GpsSpeedBufferTest {

    @Test
    fun `null until full, then null forever after`() {
        val buf = GpsSpeedBuffer(capacity = 3)
        buf.push(10f)
        buf.push(20f)
        assertNull(buf.snapshotWindow())
        buf.push(30f)
        assertArrayEquals(floatArrayOf(10f, 20f, 30f), buf.snapshotWindow(), 1e-6f)
    }

    @Test
    fun `oldest sample drops once full, most recent stays reachable`() {
        val buf = GpsSpeedBuffer(capacity = 2)
        buf.push(1f)
        buf.push(2f)
        buf.push(3f)
        assertArrayEquals(floatArrayOf(2f, 3f), buf.snapshotWindow(), 1e-6f)
        assertEquals(3f, buf.latestOrNull()!!, 1e-6f)
    }

    @Test
    fun `latestOrNull is null on an empty buffer`() {
        val buf = GpsSpeedBuffer(capacity = 3)
        assertNull(buf.latestOrNull())
    }
}
