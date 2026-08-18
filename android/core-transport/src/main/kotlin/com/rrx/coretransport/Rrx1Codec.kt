package com.rrx.coretransport

import java.math.BigInteger
import java.util.UUID
import kotlin.math.roundToLong

/**
 * On-device encoder for the RRX1 SMS wire protocol
 * (`backend/app/services/sms_protocol.py`'s `encode_rrx1()` -- that
 * function's own docstring calls it "the canonical, executable spec for
 * the Android team to mirror rather than re-derive the bit-packing from
 * prose," which is exactly what this file does). Verified against two
 * concrete outputs from the real Python implementation, not just the
 * source read-through -- see [Rrx1CodecTest].
 *
 * The PRD's own worked example CRC does not reproduce under CRC-8/ATM (or
 * any of 9 other tested variants) against the backend implementation
 * either -- `sms_protocol.py` documents this as the spec's illustrative
 * placeholder text, not a real discrepancy in the algorithm. This port
 * exists to match the *backend's* implementation exactly (so encode-here,
 * parse-there round-trips), not the PRD's unreproducible worked example.
 */
object Rrx1Codec {
    private const val ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    private val SEVERITY_CODE = mapOf("MINOR" to 1, "MODERATE" to 2, "SEVERE" to 3, "CRITICAL" to 4)

    /** CRC-8/ATM (aka CRC-8/I-432-1): poly 0x07, init 0x00, no reflection,
     * no xorout -- byte-for-byte port of `crc8_atm()`. */
    fun crc8Atm(data: ByteArray): Int {
        var crc = 0x00
        for (b in data) {
            crc = crc xor (b.toInt() and 0xFF)
            repeat(8) {
                crc = if (crc and 0x80 != 0) ((crc shl 1) xor 0x07) and 0xFF else (crc shl 1) and 0xFF
            }
        }
        return crc
    }

    /** First 65 bits of the UUID's 128-bit value, as an unsigned
     * BigInteger -- matches Python's `alert_uuid.int >> (128 - 65)`
     * exactly (Python ints are arbitrary precision; 65 bits doesn't fit a
     * JVM `Long`, hence BigInteger here rather than bit-twiddling across
     * `mostSignificantBits`/`leastSignificantBits` by hand). */
    private fun uuidPrefixBits65(uuid: UUID): BigInteger {
        val bytes = ByteArray(16)
        val msb = uuid.mostSignificantBits
        val lsb = uuid.leastSignificantBits
        for (i in 0..7) bytes[i] = (msb shr (8 * (7 - i))).toByte()
        for (i in 0..7) bytes[8 + i] = (lsb shr (8 * (7 - i))).toByte()
        val full = BigInteger(1, bytes) // unsigned 128-bit value
        return full.shiftRight(128 - 65)
    }

    private fun encodeCrockford(value: BigInteger, length: Int): String {
        val chars = CharArray(length)
        var v = value
        val mask = BigInteger.valueOf(0x1F)
        for (i in length - 1 downTo 0) {
            chars[i] = ALPHABET[v.and(mask).toInt()]
            v = v.shiftRight(5)
        }
        return String(chars)
    }

    /** Python's `round()` is banker's-rounding (round-half-to-even);
     * `roundToLong()` is round-half-up. These differ only exactly on a
     * .5 boundary, which real GPS/sensor floats essentially never land on
     * after the times-1e5 / times-10 scaling used here -- an accepted,
     * extremely-low-probability divergence rather than a byte-for-byte
     * guarantee. */
    private fun pyRound(x: Double): Long = x.roundToLong()

    fun encode(
        alertUuid: UUID,
        lat: Double,
        lon: Double,
        occurredAtEpochSeconds: Long,
        severity: String,
        speedKmh: Double,
        headingDeg: Double,
        gpsAccuracyM: Double,
        peakG: Double,
        rollover: Boolean = false,
        stillMoving: Boolean = false,
        unresponsive: Boolean = false,
        cancelWindowExpired: Boolean = true,
    ): String {
        val sevCode = SEVERITY_CODE[severity] ?: error("unknown severity: $severity")
        val flags = buildString {
            if (rollover) append('R')
            if (stillMoving) append('M')
            if (unresponsive) append('U')
            if (cancelWindowExpired) append('C')
        }
        val payload = listOf(
            "RRX1",
            encodeCrockford(uuidPrefixBits65(alertUuid), 13),
            pyRound(lat * 1e5).toString(),
            pyRound(lon * 1e5).toString(),
            occurredAtEpochSeconds.toString(),
            sevCode.toString(),
            pyRound(speedKmh).toString(),
            pyRound(headingDeg).toString(),
            pyRound(gpsAccuracyM).toString(),
            pyRound(peakG * 10).toString(),
            flags,
        ).joinToString("|")
        val crc = crc8Atm(payload.toByteArray(Charsets.US_ASCII))
        return "$payload|" + crc.toString(16).uppercase().padStart(2, '0')
    }
}
