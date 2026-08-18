package com.rrx.coresensing

import org.junit.Assert.assertEquals
import org.junit.Test

class StageAGateTest {

    @Test
    fun `below the g threshold, neither arm fires regardless of speed`() {
        val r = StageAGate.evaluate(peakAccelMagnitudeG = 1.0f, speedKmh = 100f)
        assertEquals(StageAResult(full = false, degraded = false), r)
    }

    @Test
    fun `at or above the g threshold with sufficient speed, both arms fire`() {
        val r = StageAGate.evaluate(peakAccelMagnitudeG = 4.0f, speedKmh = 20f)
        assertEquals(StageAResult(full = true, degraded = true), r)
    }

    @Test
    fun `above g but below the speed floor -- degraded fires, full does not (eliminates dropped phones)`() {
        val r = StageAGate.evaluate(peakAccelMagnitudeG = 6.0f, speedKmh = 2f)
        assertEquals(StageAResult(full = false, degraded = true), r)
    }

    @Test
    fun `no GPS fix -- degraded still fires so a real crash can't go undetected just because GPS dropped`() {
        val r = StageAGate.evaluate(peakAccelMagnitudeG = 5.0f, speedKmh = null)
        assertEquals(StageAResult(full = false, degraded = true), r)
    }

    @Test
    fun `no GPS fix and below g threshold -- neither arm fires`() {
        val r = StageAGate.evaluate(peakAccelMagnitudeG = 0.9f, speedKmh = null)
        assertEquals(StageAResult(full = false, degraded = false), r)
    }
}
