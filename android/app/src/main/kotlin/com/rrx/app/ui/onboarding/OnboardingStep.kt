package com.rrx.app.ui.onboarding

/**
 * UX-APPFLOW.md §11's nine steps. A fixed, linear sequence -- not a graph
 * -- so [OnboardingViewModel] can drive it with a plain index into
 * [OnboardingStep.ALL] rather than a state-machine's worth of per-step
 * transition rules the way [com.rrx.app.crash.CrashFlowState] needs
 * (that flow branches on cancel/expire; this one never branches, it only
 * ever advances or is skipped, and every step is reachable from onboarding
 * having started at all).
 *
 * MVP-PLAN.md §4.2's sixth consent card (continuous-microphone buffering)
 * is deliberately not a step here: nothing in this app captures real
 * microphone audio anywhere (`CrashClassifier`'s `raw_audio` input is
 * always synthetic noise, never a live signal -- see its doc comment), so
 * a consent card asking permission for a capability that doesn't exist
 * would be asking for trust this build hasn't earned. Add it when real
 * mic capture lands, not before.
 */
enum class OnboardingStep {
    Promise,
    Language,
    ConsentLocation,
    ConsentMotion,
    ConsentSms,
    Contacts,
    Medical,
    Battery,
    Ready;

    companion object {
        val ALL = entries
    }
}
