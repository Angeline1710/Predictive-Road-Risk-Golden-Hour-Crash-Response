package com.rrx.coredetection

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * On-device port of `ml/crash_detection/sensors.py`'s `saturation_features()`
 * and `ml/crash_detection/build_dataset.py`'s `gps_features()`, which
 * together produce 21 of Model A's 26 `tab` columns. Column order confirmed
 * directly against the training code (not just read from it): running both
 * functions through `pd.DataFrame` on the actual Python source, and
 * separately inspecting `crash_fusion_deployable_v1.tflite`'s real input
 * signature (`serving_default_tab:0`, shape `[1, 26]`), gives
 *
 *   sat_n_clipped, sat_frac_clipped, sat_axes_clipped, sat_simultaneous,
 *   sat_longest_run, sat_longest_run_ms, sat_onset_slope, sat_rail_g,
 *   imu_impulse, imu_peak_obs_g, imu_rms_g, gps_v0, gps_v_end,
 *   gps_drop_kmh, gps_drop_frac, gps_max_decel_kmh_s, gps_decel_ratio,
 *   gps_v_min, gps_settled, gyro_peak_dps, gyro_integral_deg,
 *   aud_peak_db, aud_snr_db, aud_crest, aud_onset_slope, aud_zcr
 *
 * The last 5 columns are audio-derived (`ml/crash_detection/audio_data.py`'s
 * `acoustic_features()`) and are always zero here -- **not because they're
 * unimplemented, but because zero is the actually-correct value**: this
 * scaffold has no microphone capture (MVP-PLAN.md §4.2 -- continuous mic
 * buffering needs a consent card that doesn't exist yet), and
 * `ml/crash_detection/train.py`'s own inference-degradation harness states
 * outright that "zeroing an input reproduces exactly what ModalityDropout
 * trained for." Feeding zeros here is therefore reproducing a validated
 * training-time condition, not guessing at a missing modality's value.
 *
 * Getting the column order wrong would silently feed the trained model's
 * Dense layer a scrambled feature vector -- there's no shape mismatch to
 * catch it, since it's still 26 floats. [TabularFeaturesTest] pins this
 * order by asserting field-by-field on a hand-computed example, not just
 * checking the array length.
 */
object TabularFeatures {
    const val N_TAB = 26
    private const val N_AUD_ZERO = 5

    /**
     * @param imuWindow (200, 9) -- accel xyz (already clamped to the rail),
     *   gyro xyz, clip-mask xyz, i.e. exactly [ImuRingBuffer.snapshotWindow]'s
     *   layout.
     * @param accelRailG the same rail [ImuRingBuffer] clamped against --
     *   becomes the `sat_rail_g` feature verbatim, matching training where
     *   it's a per-device sampled constant, not a derived statistic.
     * @param gpsWindow (12,) km/h, i.e. [GpsSpeedBuffer.snapshotWindow]'s layout.
     */
    fun extract(imuWindow: Array<FloatArray>, accelRailG: Float, gpsWindow: FloatArray): FloatArray {
        val n = imuWindow.size
        val mag = FloatArray(n)
        val anyClip = BooleanArray(n)
        var nClipped = 0
        val axisClippedAny = booleanArrayOf(false, false, false)
        var simultaneous = 0

        for (i in 0 until n) {
            val row = imuWindow[i]
            mag[i] = sqrt(row[0] * row[0] + row[1] * row[1] + row[2] * row[2])
            val cx = row[6] > 0f
            val cy = row[7] > 0f
            val cz = row[8] > 0f
            if (cx) { nClipped++; axisClippedAny[0] = true }
            if (cy) { nClipped++; axisClippedAny[1] = true }
            if (cz) { nClipped++; axisClippedAny[2] = true }
            val axisCount = (if (cx) 1 else 0) + (if (cy) 1 else 0) + (if (cz) 1 else 0)
            if (axisCount >= 2) simultaneous++
            anyClip[i] = axisCount > 0
        }

        var longestRun = 0
        var currentRun = 0
        var firstClipIdx = -1
        for (i in 0 until n) {
            if (anyClip[i]) {
                if (firstClipIdx == -1) firstClipIdx = i
                currentRun++
                if (currentRun > longestRun) longestRun = currentRun
            } else {
                currentRun = 0
            }
        }

        var onsetSlope = 0f
        if (nClipped > 0) {
            val lo = max(0, firstClipIdx - 5)
            if (firstClipIdx > lo) {
                onsetSlope = (mag[firstClipIdx] - mag[lo]) / (firstClipIdx - lo)
            }
        }

        var magSum = 0f
        var magSqSum = 0f
        var magMax = 0f
        for (v in mag) {
            magSum += v
            magSqSum += v * v
            if (v > magMax) magMax = v
        }
        val impulse = magSum / SensingHz.IMU_HZ
        val rmsG = sqrt(magSqSum / n)

        var gyroPeak = 0f
        var gyroAbsSum = 0f
        for (row in imuWindow) {
            for (axis in 3..5) {
                val a = abs(row[axis])
                if (a > gyroPeak) gyroPeak = a
                gyroAbsSum += a
            }
        }
        val gyroIntegralDeg = gyroAbsSum / SensingHz.IMU_HZ

        val gps = GpsFeatures.extract(gpsWindow)

        // Trailing N_AUD_ZERO entries are aud_peak_db, aud_snr_db,
        // aud_crest, aud_onset_slope, aud_zcr -- see the class doc comment
        // for why zero, not a DSP computation on absent audio, is correct.
        return floatArrayOf(
            nClipped.toFloat(),
            nClipped.toFloat() / (n * 3),
            axisClippedAny.count { it }.toFloat(),
            simultaneous.toFloat(),
            longestRun.toFloat(),
            longestRun.toFloat() / SensingHz.IMU_HZ * 1000f,
            onsetSlope,
            accelRailG,
            impulse,
            magMax,
            rmsG,
            gps.v0, gps.vEnd, gps.dropKmh, gps.dropFrac, gps.maxDecelKmhS,
            gps.decelRatio, gps.vMin, gps.settled,
            gyroPeak,
            gyroIntegralDeg,
            *FloatArray(N_AUD_ZERO),
        )
    }
}

/** Kept separate from [SensingConfig] in core-sensing -- core-detection
 * doesn't depend on core-sensing, only on the array shapes it produces. */
internal object SensingHz {
    const val IMU_HZ = 50
}

internal data class GpsFeatureSet(
    val v0: Float, val vEnd: Float, val dropKmh: Float, val dropFrac: Float,
    val maxDecelKmhS: Float, val decelRatio: Float, val vMin: Float, val settled: Float,
)

internal object GpsFeatures {
    private const val GPS_IMPACT_IDX = 8

    fun extract(v: FloatArray): GpsFeatureSet {
        val pre = median(v.copyOfRange(0, GPS_IMPACT_IDX))
        val tail = if (v.size > GPS_IMPACT_IDX + 2) v.copyOfRange(GPS_IMPACT_IDX + 2, v.size) else null
        val post = tail?.let { median(it) } ?: v.last()

        val diffs = FloatArray(v.size - 1) { v[it + 1] - v[it] }
        val maxDecel = if (diffs.isNotEmpty()) -diffs.min() else 0f

        val totalDrop = max(0f, pre - post)
        val ratio = if (totalDrop > 1f) maxDecel / (totalDrop + 1e-6f) else 0f

        return GpsFeatureSet(
            v0 = pre,
            vEnd = post,
            dropKmh = totalDrop,
            dropFrac = totalDrop / (pre + 1e-6f),
            maxDecelKmhS = maxDecel,
            decelRatio = ratio,
            vMin = v.min(),
            settled = tail?.let { stddev(it) } ?: 0f,
        )
    }

    private fun median(a: FloatArray): Float {
        val sorted = a.sortedArray()
        val mid = sorted.size / 2
        return if (sorted.size % 2 == 0) (sorted[mid - 1] + sorted[mid]) / 2f else sorted[mid]
    }

    private fun stddev(a: FloatArray): Float {
        val mean = a.average().toFloat()
        val variance = a.sumOf { ((it - mean) * (it - mean)).toDouble() } / a.size
        return sqrt(variance).toFloat()
    }
}
