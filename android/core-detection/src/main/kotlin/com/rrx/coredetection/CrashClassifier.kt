package com.rrx.coredetection

import android.content.Context
import android.content.res.AssetFileDescriptor
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import kotlin.random.Random

enum class IncidentSeverity { MINOR, MODERATE, SEVERE, CRITICAL, NONE }

data class CrashPrediction(val pCrash: Float, val severity: IncidentSeverity, val severityProbs: FloatArray) {
    override fun equals(other: Any?): Boolean =
        other is CrashPrediction && pCrash == other.pCrash && severity == other.severity &&
            severityProbs.contentEquals(other.severityProbs)

    override fun hashCode(): Int = 31 * (31 * pCrash.hashCode() + severity.hashCode()) + severityProbs.contentHashCode()
}

/**
 * Loads `crash_fusion_deployable_v1.tflite` (bundled in this module's
 * assets) and runs it via its named `serving_default` signature --
 * `{imu, gps, tab, raw_audio} -> {output_0: crash, output_1: severity}`,
 * confirmed directly against the real exported artifact (not assumed from
 * the Keras source): `interp.get_signature_list()` on the actual .tflite
 * file.
 *
 * **raw_audio is never real microphone data in this build.** There is no
 * consent flow for continuous mic capture yet (MVP-PLAN.md §4.2), so this
 * class feeds low-amplitude noise instead. That is a deliberate, verified
 * choice, not a placeholder-and-forget: feeding *exact* digital silence
 * (an all-zero raw_audio tensor) was tested directly against this artifact
 * and produces **NaN on every output**, almost certainly a `log(0)`
 * singularity in the baked-in mel frontend (ml/crash_detection/mel_frontend.py).
 * Amplitude 1e-6 already avoids it; this class uses 1e-4 (a physically
 * negligible "noise floor" stand-in, closer to what a real quiet cabin
 * would look like than literal silence would be anyway) for headroom.
 * Detection quality from the audio branch is effectively disabled until
 * real capture lands -- IMU and GPS drive the score in this build, which
 * is the condition `ml/MODELS.md` already reports as validated (recall
 * held at 1.000 with audio removed in evaluation).
 */
class CrashClassifier(context: Context) : AutoCloseable {

    private val interpreter: Interpreter = Interpreter(loadModelFile(context))

    fun classify(imuWindow: Array<FloatArray>, gpsWindow: FloatArray, tab: FloatArray): CrashPrediction {
        require(imuWindow.size == WIN_LEN) { "imuWindow must have $WIN_LEN rows, got ${imuWindow.size}" }
        require(tab.size == TabularFeatures.N_TAB) { "tab must have ${TabularFeatures.N_TAB} entries, got ${tab.size}" }

        val inputs = mapOf(
            "imu" to arrayOf(imuWindow),
            "gps" to arrayOf(gpsWindow),
            "tab" to arrayOf(tab),
            "raw_audio" to arrayOf(silentAudioPlaceholder()),
        )
        val crashOut = Array(1) { FloatArray(1) }
        val severityOut = Array(1) { FloatArray(5) }
        val outputs = mutableMapOf<String, Any>("output_0" to crashOut, "output_1" to severityOut)

        interpreter.runSignature(inputs, outputs, "serving_default")

        val probs = severityOut[0]
        // Index 4 = the model's explicit NONE class; 0-3 follow
        // ml/common/config.py's SEVERITY order (MINOR..CRITICAL). Confirmed
        // empirically for the NONE case (every negative-class test run
        // against the real artifact put all mass on index 4); the positive
        // classes are inferred from model.py's own comment
        // ("4 severity bands plus an explicit NONE for negatives") and
        // ml/common/config.py's SEVERITY list order, not independently
        // triggered in verification -- crafting a properly
        // training-distribution-shaped positive sample was out of scope
        // for this pass.
        val severity = IncidentSeverity.entries[probs.indices.maxBy { probs[it] }]

        return CrashPrediction(pCrash = crashOut[0][0], severity = severity, severityProbs = probs)
    }

    override fun close() {
        interpreter.close()
    }

    private fun silentAudioPlaceholder(): FloatArray =
        FloatArray(AUDIO_LEN) { (rng.nextDouble(-1.0, 1.0) * NOISE_FLOOR_AMPLITUDE).toFloat() }

    private val rng = Random(System.nanoTime())

    companion object {
        // Deliberately duplicated from core-sensing's SensingConfig.WIN_LEN
        // rather than imported -- core-detection doesn't depend on
        // core-sensing (see TabularFeatures.kt's SensingHz for the same
        // reasoning), so this is the module boundary's cost. Both values
        // are 200 because both are "4s at 50Hz" per ml/common/config.py;
        // if one changes, the other must too.
        const val WIN_LEN = 200
        const val AUDIO_LEN = 64_000
        private const val NOISE_FLOOR_AMPLITUDE = 1e-4
        const val ASSET_NAME = "crash_fusion_deployable_v1.tflite"

        private fun loadModelFile(context: Context): MappedByteBuffer {
            val afd: AssetFileDescriptor = context.assets.openFd(ASSET_NAME)
            FileInputStream(afd.fileDescriptor).use { input ->
                return input.channel.map(FileChannel.MapMode.READ_ONLY, afd.startOffset, afd.declaredLength)
            }
        }
    }
}
