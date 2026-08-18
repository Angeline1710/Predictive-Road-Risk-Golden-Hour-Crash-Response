package com.rrx.app.device

import android.content.Context
import android.provider.Settings
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * PRD.md NFR-PR4: "Salted hash of ANDROID_ID -- the backend never sees a
 * raw hardware identifier" (backend/app/models/device.py's `device_hash`
 * column comment says the same thing). The salt should be a per-install
 * random value persisted in EncryptedSharedPreferences (core-data, not
 * built yet -- see core-data/.../Placeholder.kt); this scaffold generates
 * a fresh salt per process instead, which is real hashing behaviour but
 * not yet a stable per-install identity across app restarts.
 */
object DeviceIdentity {

    private val processSalt: ByteArray = ByteArray(16).also { SecureRandom().nextBytes(it) }

    @Suppress("HardwareIds")
    fun saltedHash(context: Context): String {
        val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
        val digest = MessageDigest.getInstance("SHA-256")
        digest.update(processSalt)
        digest.update(androidId.toByteArray(Charsets.UTF_8))
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
