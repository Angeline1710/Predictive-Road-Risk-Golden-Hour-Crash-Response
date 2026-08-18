package com.rrx.app.ui.onboarding

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.res.stringResource
import com.rrx.app.R

/**
 * UX-APPFLOW.md §11.3: "One permission per screen. Never a batch
 * request." -- each screen below uses [ActivityResultContracts.RequestPermission],
 * the single-permission contract, never [ActivityResultContracts.RequestMultiplePermissions]
 * ([com.rrx.app.ui.drive.DriveSection]'s pattern, which is correct there
 * because Drive Mode is requesting permissions it already has independent
 * consent for, not re-litigating first consent).
 */
@Composable
fun LocationConsentScreen(viewModel: OnboardingViewModel) {
    // ACCESS_BACKGROUND_LOCATION cannot be requested in the same dialog as
    // foreground location on API 30+ (the system silently ignores it if
    // you try) -- it has to be a genuinely separate follow-up request
    // once foreground is granted, which is exactly what happens below.
    val backgroundLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {
        viewModel.setConsentLocation(true)
    }
    val foregroundLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (!granted) {
            viewModel.setConsentLocation(false)
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            backgroundLauncher.launch(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
        } else {
            viewModel.setConsentLocation(true)
        }
    }

    ConsentCardScreen(
        overline = stringResource(R.string.consent_location_title),
        reason = stringResource(R.string.consent_location_reason),
        doList = listOf(
            stringResource(R.string.consent_location_do_1),
            stringResource(R.string.consent_location_do_2),
        ),
        dontList = listOf(
            stringResource(R.string.consent_location_dont_1),
            stringResource(R.string.consent_location_dont_2),
        ),
        whatWeStore = stringResource(R.string.consent_location_stores),
        allowLabel = stringResource(R.string.consent_location_cta),
        onAllow = { foregroundLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION) },
        onNotNow = { viewModel.setConsentLocation(false) },
    )
}

@Composable
fun MotionConsentScreen(viewModel: OnboardingViewModel) {
    // ACTIVITY_RECOGNITION is only a runtime-requestable permission from
    // API 29 (Q) -- below that it's a normal manifest permission, granted
    // at install time, so there's nothing to request.
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        viewModel.setConsentMotion(granted)
    }
    val needsRuntimeRequest = remember { Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q }

    ConsentCardScreen(
        overline = stringResource(R.string.consent_motion_title),
        reason = stringResource(R.string.consent_motion_reason),
        doList = listOf(
            stringResource(R.string.consent_motion_do_1),
            stringResource(R.string.consent_motion_do_2),
        ),
        dontList = listOf(
            stringResource(R.string.consent_motion_dont_1),
            stringResource(R.string.consent_motion_dont_2),
        ),
        whatWeStore = stringResource(R.string.consent_motion_stores),
        allowLabel = stringResource(R.string.consent_motion_cta),
        onAllow = {
            if (needsRuntimeRequest) {
                launcher.launch(Manifest.permission.ACTIVITY_RECOGNITION)
            } else {
                viewModel.setConsentMotion(true)
            }
        },
        onNotNow = { viewModel.setConsentMotion(false) },
    )
}

@Composable
fun SmsConsentScreen(viewModel: OnboardingViewModel) {
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        viewModel.setConsentSms(granted)
    }

    ConsentCardScreen(
        overline = stringResource(R.string.consent_sms_title),
        reason = stringResource(R.string.consent_sms_reason),
        doList = listOf(
            stringResource(R.string.consent_sms_do_1),
            stringResource(R.string.consent_sms_do_2),
        ),
        dontList = listOf(
            stringResource(R.string.consent_sms_dont_1),
            stringResource(R.string.consent_sms_dont_2),
        ),
        whatWeStore = stringResource(R.string.consent_sms_stores),
        allowLabel = stringResource(R.string.consent_sms_cta),
        extraLine = stringResource(R.string.consent_sms_extra_line),
        onAllow = { launcher.launch(Manifest.permission.SEND_SMS) },
        onNotNow = { viewModel.setConsentSms(false) },
    )
}
