package com.rrx.app.device

import android.content.Context
import android.provider.Settings
import android.util.Base64
import com.rrx.coredata.OnboardingStore
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * PRD.md NFR-PR4: "Salted hash of ANDROID_ID -- the backend never sees a
 * raw hardware identifier" (backend/app/models/device.py's `device_hash`
 * column comment says the same thing). The salt is a per-install random
 * value persisted via [OnboardingStore] (core-data, real as of the
 * onboarding pass) -- generated once and reused on every call, so the
 * hash is a stable per-install identity across app restarts rather than
 * rotating every cold start the way a process-lifetime salt would.
 */
object DeviceIdentity {

    @Suppress("HardwareIds")
    fun saltedHash(context: Context, store: OnboardingStore): String {
        val salt = salt(store)
        val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
        val digest = MessageDigest.getInstance("SHA-256")
        digest.update(salt)
        digest.update(androidId.toByteArray(Charsets.UTF_8))
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun salt(store: OnboardingStore): ByteArray {
        store.deviceSaltBase64?.let { return Base64.decode(it, Base64.NO_WRAP) }
        val fresh = ByteArray(16).also { SecureRandom().nextBytes(it) }
        store.deviceSaltBase64 = Base64.encodeToString(fresh, Base64.NO_WRAP)
        return fresh
    }
}
