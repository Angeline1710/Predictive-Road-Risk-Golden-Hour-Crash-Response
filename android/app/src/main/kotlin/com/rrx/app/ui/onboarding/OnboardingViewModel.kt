package com.rrx.app.ui.onboarding

import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rrx.coredata.EmergencyContact
import com.rrx.coredata.EmergencyContactDao
import com.rrx.coredata.OnboardingStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

/** UX-APPFLOW.md §11.4's medical profile fields, held as in-progress UI
 * state until [OnboardingViewModel.saveMedicalAndContinue] persists them --
 * "All optional, each with an explicit skip," so nothing here is written
 * to [OnboardingStore] until the user actually leaves the step, skip or not. */
data class MedicalFormState(
    val bloodGroup: String? = null,
    val allergies: String = "",
    val conditions: String = "",
    val organDonor: Boolean? = null,
)

/**
 * Drives UX-APPFLOW.md §11's nine-step sequence. Unlike
 * [com.rrx.app.crash.CrashCountdownViewModel], every step here is a plain
 * forward advance (or a skip, which is also just an advance) -- there's no
 * cancel/expire branching, so a single [currentStep] index is enough
 * state, no sealed-interface state machine needed.
 */
@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val onboardingStore: OnboardingStore,
    private val contactDao: EmergencyContactDao,
) : ViewModel() {

    private val _currentStep = MutableStateFlow(OnboardingStep.ALL.first())
    val currentStep: StateFlow<OnboardingStep> = _currentStep.asStateFlow()

    val contacts: StateFlow<List<EmergencyContact>> = contactDao.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _selectedLanguage = MutableStateFlow(
        OnboardingLanguages.firstOrNull { it.tag == onboardingStore.languageTag } ?: OnboardingLanguages.first()
    )
    val selectedLanguage: StateFlow<OnboardingLanguage> = _selectedLanguage.asStateFlow()

    private val _medicalForm = MutableStateFlow(MedicalFormState())
    val medicalForm: StateFlow<MedicalFormState> = _medicalForm.asStateFlow()

    // Seeded from the persisted flag, not hardcoded false -- a returning
    // user whose device already completed onboarding must not be sent
    // through it again just because a fresh ViewModel instance was
    // created for this cold start.
    private val _finished = MutableStateFlow(onboardingStore.hasCompletedOnboarding)
    /** [MainActivity] observes this to swap `OnboardingFlowHost` for
     * `HomeScreen` once the flow completes -- see that file's doc comment
     * for why this is a flag flip and not a navigation-library route
     * change. */
    val finished: StateFlow<Boolean> = _finished.asStateFlow()

    fun advance() {
        val steps = OnboardingStep.ALL
        val nextIndex = steps.indexOf(_currentStep.value) + 1
        if (nextIndex >= steps.size) {
            onboardingStore.hasCompletedOnboarding = true
            _finished.value = true
        } else {
            _currentStep.value = steps[nextIndex]
        }
    }

    fun back() {
        val steps = OnboardingStep.ALL
        val prevIndex = steps.indexOf(_currentStep.value) - 1
        if (prevIndex >= 0) _currentStep.value = steps[prevIndex]
    }

    fun selectLanguage(language: OnboardingLanguage) {
        _selectedLanguage.value = language
        onboardingStore.languageTag = language.tag
        // AppCompat's per-app language backport -- works down to minSdk
        // 26, not just the API 33+ OS-level per-app-language setting.
        // null tag -> empty LocaleListCompat, i.e. "no override, follow
        // the system/app default (English)."
        AppCompatDelegate.setApplicationLocales(
            language.tag?.let { LocaleListCompat.forLanguageTags(it) } ?: LocaleListCompat.getEmptyLocaleList()
        )
    }

    fun setConsentLocation(granted: Boolean) {
        onboardingStore.consentLocation = granted
        advance()
    }

    fun setConsentMotion(granted: Boolean) {
        onboardingStore.consentMotion = granted
        advance()
    }

    fun setConsentSms(granted: Boolean) {
        onboardingStore.consentSms = granted
        advance()
    }

    /** Read by [ReadyScreen] -- the SMS fallback status line reports what
     * was actually granted on the consent card two steps back, not an
     * optimistic assumption. */
    fun smsConsentGranted(): Boolean = onboardingStore.consentSms

    fun addContact(contact: EmergencyContact) {
        viewModelScope.launch {
            // UX-APPFLOW.md §11.4: "Up to 5" -- enforced here, not just in
            // the picker UI, since the picker itself has no concept of a
            // limit.
            if (contactDao.count() >= MAX_CONTACTS) return@launch
            contactDao.insert(contact.copy(priority = contactDao.count() + 1))
        }
    }

    fun removeContact(contact: EmergencyContact) {
        viewModelScope.launch { contactDao.delete(contact) }
    }

    fun updateMedicalForm(transform: (MedicalFormState) -> MedicalFormState) {
        _medicalForm.value = transform(_medicalForm.value)
    }

    /** Called on both "Continue" and "Skip" -- UX-APPFLOW.md §11.4's
     * fields are all optional, so skipping is just continuing with
     * whatever (possibly nothing) was filled in. */
    fun saveMedicalAndContinue() {
        val form = _medicalForm.value
        onboardingStore.bloodGroup = form.bloodGroup
        onboardingStore.allergies = form.allergies.ifBlank { null }
        onboardingStore.conditions = form.conditions.ifBlank { null }
        onboardingStore.organDonor = form.organDonor
        advance()
    }

    companion object {
        const val MAX_CONTACTS = 5
    }
}
