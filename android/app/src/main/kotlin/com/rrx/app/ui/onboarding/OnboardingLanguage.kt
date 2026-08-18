package com.rrx.app.ui.onboarding

/**
 * PRD.md §7/§12.3 and UX-APPFLOW.md §6.4: "Five languages at demo:
 * English, हिन्दी, தமிழ், తెలుగు, বাংলা." [tag] is a BCP-47 language tag,
 * used both for [androidx.appcompat.app.AppCompatDelegate.setApplicationLocales]
 * and for building the `java.util.Locale` an onboarding TTS preview
 * speaks in -- `null` means "no override," i.e. English via the app's
 * unlocalized default resources rather than a real `en` override.
 */
data class OnboardingLanguage(val tag: String?, val nativeName: String, val englishName: String)

val OnboardingLanguages = listOf(
    OnboardingLanguage(tag = null, nativeName = "English", englishName = "English"),
    OnboardingLanguage(tag = "hi", nativeName = "हिन्दी", englishName = "Hindi"),
    OnboardingLanguage(tag = "ta", nativeName = "தமிழ்", englishName = "Tamil"),
    OnboardingLanguage(tag = "te", nativeName = "తెలుగు", englishName = "Telugu"),
    OnboardingLanguage(tag = "bn", nativeName = "বাংলা", englishName = "Bengali"),
)
