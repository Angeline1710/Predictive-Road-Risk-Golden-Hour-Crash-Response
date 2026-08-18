package com.rrx.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import com.rrx.app.ui.home.HomeScreen
import com.rrx.app.ui.onboarding.OnboardingFlowHost
import com.rrx.app.ui.onboarding.OnboardingViewModel
import com.rrx.app.ui.theme.RrxTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RrxTheme {
                RrxApp()
            }
        }
    }
}

/**
 * Gates [HomeScreen] behind [OnboardingFlowHost] until UX-APPFLOW.md
 * §11's flow completes -- `hiltViewModel()` with no arguments resolves to
 * the nearest [androidx.lifecycle.ViewModelStoreOwner] (this Activity),
 * so this call and the one inside `OnboardingFlowHost` return the same
 * [OnboardingViewModel] instance; there's no navigation library in this
 * scaffold to hand a shared instance through explicitly (see
 * [com.rrx.app.crash.CrashFlowHost]'s doc comment for the same reasoning
 * applied to the crash flow).
 */
@Composable
private fun RrxApp(viewModel: OnboardingViewModel = hiltViewModel()) {
    val finished by viewModel.finished.collectAsState()
    if (finished) HomeScreen() else OnboardingFlowHost(viewModel)
}
