package com.rrx.coredata

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * PRD.md §12.6 / NFR-S2: consent flags, medical profile, and the selected
 * language, "encrypted at rest" via Android Keystore + EncryptedSharedPreferences
 * -- UX-APPFLOW.md §11.4's encryption line ("Encrypted on this device")
 * is literal, not marketing copy. [EmergencyContact] rows live in Room
 * instead (see [RrxDatabase]) since they're an ordered list, not scalars;
 * Room itself has no at-rest encryption here, a real gap noted in
 * android/README.md -- SQLCipher would close it but is out of scope for
 * this pass.
 *
 * Also owns [deviceSalt]: `DeviceIdentity`'s own doc comment already
 * named this exact class as where its process-lifetime-only salt should
 * end up once core-data existed.
 */
class OnboardingStore(context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "rrx_onboarding_secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    var hasCompletedOnboarding: Boolean
        get() = prefs.getBoolean(KEY_ONBOARDING_DONE, false)
        set(value) = prefs.edit().putBoolean(KEY_ONBOARDING_DONE, value).apply()

    /** BCP-47 language tag ("hi", "ta", "te", "bn") or null for English/
     * system default -- mirrors what [androidx.appcompat.app.AppCompatDelegate]
     * expects `setApplicationLocales` to be given. */
    var languageTag: String?
        get() = prefs.getString(KEY_LANGUAGE, null)
        set(value) = prefs.edit().putString(KEY_LANGUAGE, value).apply()

    var consentLocation: Boolean
        get() = prefs.getBoolean(KEY_CONSENT_LOCATION, false)
        set(value) = prefs.edit().putBoolean(KEY_CONSENT_LOCATION, value).apply()

    var consentMotion: Boolean
        get() = prefs.getBoolean(KEY_CONSENT_MOTION, false)
        set(value) = prefs.edit().putBoolean(KEY_CONSENT_MOTION, value).apply()

    var consentSms: Boolean
        get() = prefs.getBoolean(KEY_CONSENT_SMS, false)
        set(value) = prefs.edit().putBoolean(KEY_CONSENT_SMS, value).apply()

    /** UX-APPFLOW.md §11.4: "All optional, each with an explicit skip" --
     * null throughout means every field was skipped, not that the store
     * failed to read. */
    var bloodGroup: String?
        get() = prefs.getString(KEY_BLOOD_GROUP, null)
        set(value) = prefs.edit().putString(KEY_BLOOD_GROUP, value).apply()

    var allergies: String?
        get() = prefs.getString(KEY_ALLERGIES, null)
        set(value) = prefs.edit().putString(KEY_ALLERGIES, value).apply()

    var conditions: String?
        get() = prefs.getString(KEY_CONDITIONS, null)
        set(value) = prefs.edit().putString(KEY_CONDITIONS, value).apply()

    var organDonor: Boolean?
        get() = if (prefs.contains(KEY_ORGAN_DONOR)) prefs.getBoolean(KEY_ORGAN_DONOR, false) else null
        set(value) = prefs.edit().apply {
            if (value == null) remove(KEY_ORGAN_DONOR) else putBoolean(KEY_ORGAN_DONOR, value)
        }.apply()

    /** Base64 of the 16-byte salt `DeviceIdentity.saltedHash()` mixes into
     * `ANDROID_ID` -- persisted here so device identity survives process
     * restarts instead of silently rotating every cold start. */
    var deviceSaltBase64: String?
        get() = prefs.getString(KEY_DEVICE_SALT, null)
        set(value) = prefs.edit().putString(KEY_DEVICE_SALT, value).apply()

    private companion object {
        const val KEY_ONBOARDING_DONE = "onboarding_done"
        const val KEY_LANGUAGE = "language_tag"
        const val KEY_CONSENT_LOCATION = "consent_location"
        const val KEY_CONSENT_MOTION = "consent_motion"
        const val KEY_CONSENT_SMS = "consent_sms"
        const val KEY_BLOOD_GROUP = "medical_blood_group"
        const val KEY_ALLERGIES = "medical_allergies"
        const val KEY_CONDITIONS = "medical_conditions"
        const val KEY_ORGAN_DONOR = "medical_organ_donor"
        const val KEY_DEVICE_SALT = "device_salt"
    }
}
