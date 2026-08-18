package com.rrx.coredetection

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class TabularFeaturesTest {

    @Test
    fun `array length is 26, and the trailing 5 audio columns are exactly zero`() {
        val imu = arrayOf(floatArrayOf(0f, 0f, 1f, 0f, 0f, 0f, 0f, 0f, 0f))
        val gps = FloatArray(12) { 40f }
        val result = TabularFeatures.extract(imu, accelRailG = 8f, gpsWindow = gps)

        assertEquals(26, result.size)
        assertArrayEquals(FloatArray(5), result.copyOfRange(21, 26), 0f)
    }

    @Test
    fun `hand-computed example pins the full column order and values`() {
        // 3-sample IMU window: [ax,ay,az,gx,gy,gz,clipx,clipy,clipz].
        // Row 1's x-axis is clipped; nothing else is.
        val imu = arrayOf(
            floatArrayOf(3f, 4f, 0f, 10f, 0f, 0f, 0f, 0f, 0f),   // mag=5
            floatArrayOf(8f, 0f, 0f, 0f, 0f, 0f, 1f, 0f, 0f),    // mag=8, clip x
            floatArrayOf(0f, 0f, 2f, 0f, -20f, 0f, 0f, 0f, 0f),  // mag=2
        )
        val gps = floatArrayOf(60f, 58f, 56f, 54f, 52f, 50f, 48f, 46f, 10f, 8f, 5f, 4f)

        val r = TabularFeatures.extract(imu, accelRailG = 8f, gpsWindow = gps)

        val expected = floatArrayOf(
            /* sat_n_clipped       */ 1f,
            /* sat_frac_clipped    */ 1f / 9f,
            /* sat_axes_clipped    */ 1f,
            /* sat_simultaneous    */ 0f,
            /* sat_longest_run     */ 1f,
            /* sat_longest_run_ms  */ 20f,       // 1 / 50 * 1000
            /* sat_onset_slope     */ 3f,        // (mag[1]-mag[0]) / (1-0) = (8-5)/1
            /* sat_rail_g          */ 8f,
            /* imu_impulse         */ 0.3f,      // (5+8+2) / 50
            /* imu_peak_obs_g      */ 8f,
            /* imu_rms_g           */ 5.567764f, // sqrt((25+64+4)/3)
            /* gps_v0              */ 53f,       // median(60..46 step -2)
            /* gps_v_end           */ 4.5f,      // median(5,4)
            /* gps_drop_kmh        */ 48.5f,
            /* gps_drop_frac       */ 48.5f / 53f,
            /* gps_max_decel_kmh_s */ 36f,        // biggest single-step drop: 46->10
            /* gps_decel_ratio     */ 36f / 48.5f,
            /* gps_v_min           */ 4f,
            /* gps_settled         */ 0.5f,       // stddev(5,4)
            /* gyro_peak_dps       */ 20f,        // |-20|
            /* gyro_integral_deg   */ 0.6f,       // (10+0+20) / 50
            0f, 0f, 0f, 0f, 0f,                    // aud_* -- see class doc comment
        )
        assertEquals(26, expected.size)
        assertArrayEquals(expected, r, 1e-3f)
    }
}
