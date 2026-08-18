package com.rrx.app.ui.onboarding

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel

/** Same "one state, one `when`, no navigation library" pattern as
 * [com.rrx.app.crash.CrashFlowHost] -- see [OnboardingStep]'s doc comment
 * for why this one is a plain linear index rather than a sealed
 * interface. */
@Composable
fun OnboardingFlowHost(viewModel: OnboardingViewModel = hiltViewModel()) {
    val step by viewModel.currentStep.collectAsState()

    when (step) {
        OnboardingStep.Promise -> PromiseScreen(onNext = viewModel::advance)
        OnboardingStep.Language -> LanguageScreen(viewModel)
        OnboardingStep.ConsentLocation -> LocationConsentScreen(viewModel)
        OnboardingStep.ConsentMotion -> MotionConsentScreen(viewModel)
        OnboardingStep.ConsentSms -> SmsConsentScreen(viewModel)
        OnboardingStep.Contacts -> ContactsScreen(viewModel)
        OnboardingStep.Medical -> MedicalScreen(viewModel)
        OnboardingStep.Battery -> BatteryScreen(viewModel)
        OnboardingStep.Ready -> ReadyScreen(viewModel)
    }
}
