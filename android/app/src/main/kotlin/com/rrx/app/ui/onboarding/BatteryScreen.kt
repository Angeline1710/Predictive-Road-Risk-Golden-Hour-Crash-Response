package com.rrx.app.ui.onboarding

import android.content.Intent
import android.os.PowerManager
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.getSystemService
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner
import com.rrx.app.R
import com.rrx.app.ui.theme.Bitumen000
import com.rrx.app.ui.theme.Flare500
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.TypeDisplay2

private fun isIgnoringBatteryOptimizations(context: android.content.Context): Boolean {
    val powerManager = context.getSystemService<PowerManager>() ?: return false
    return powerManager.isIgnoringBatteryOptimizations(context.packageName)
}

/**
 * UX-APPFLOW.md §11.5. "Detect the OEM and render brand-specific
 * instructions" with Xiaomi/Oppo/Vivo/Realme-specific settings deep
 * links is explicitly **not** built here -- those intents (component
 * names, action strings) are undocumented, vendor-specific, and change
 * across ROM versions; shipping guessed intents this project has no
 * matching hardware to verify against would be exactly the kind of
 * unverified claim `ml/MODELS.md` and this whole build have deliberately
 * avoided elsewhere. `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS` (the
 * one real, documented, universal deep link the spec's own text names as
 * the fallback) is what every device gets. The verification half of the
 * spec -- "never claim success without verifying it" -- is real:
 * [PowerManager.isIgnoringBatteryOptimizations] is checked on every
 * `ON_RESUME`, not just once.
 */
@Composable
fun BatteryScreen(viewModel: OnboardingViewModel) {
    val context = LocalContext.current
    var protectionActive by remember { mutableStateOf(isIgnoringBatteryOptimizations(context)) }

    // ComponentActivity (which hosts this Compose tree) implements
    // LifecycleOwner itself -- casting the Context avoids depending on
    // the separate lifecycle-runtime-compose artifact for just one
    // ON_RESUME check.
    val lifecycleOwner = context as LifecycleOwner
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                protectionActive = isIgnoringBatteryOptimizations(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Column(modifier = Modifier.fillMaxSize().background(Bitumen000).padding(24.dp)) {
        Text(stringResource(R.string.onboarding_battery_headline), style = TypeDisplay2, color = InkInverse)
        Text(
            stringResource(R.string.onboarding_battery_body),
            color = Paper100.copy(alpha = 0.8f),
            modifier = Modifier.padding(top = 16.dp),
        )

        Column(
            modifier = Modifier
                .padding(top = 20.dp)
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(if (protectionActive) Highway300.copy(alpha = 0.15f) else Flare500.copy(alpha = 0.15f))
                .padding(16.dp),
        ) {
            Text(
                if (protectionActive) {
                    stringResource(R.string.onboarding_battery_protection_active)
                } else {
                    stringResource(R.string.onboarding_battery_protection_limited)
                },
                color = if (protectionActive) Highway300 else Flare500,
            )
        }

        if (!protectionActive) {
            Button(
                onClick = { context.startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)) },
                modifier = Modifier.padding(top = 20.dp).fillMaxWidth().height(56.dp),
            ) {
                Text(stringResource(R.string.onboarding_battery_cta))
            }
        }

        Button(
            onClick = viewModel::advance,
            modifier = Modifier.padding(top = 12.dp).fillMaxWidth().height(56.dp),
        ) {
            Text(stringResource(R.string.onboarding_battery_continue))
        }
    }
}
