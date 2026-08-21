package com.rrx.app.ui.drivemode

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.rrx.app.ui.theme.RrxTheme
import dagger.hilt.android.AndroidEntryPoint

/** Hosts [DriveModeScreen] -- a plain Activity, not a route within
 * `MainActivity`'s composable tree, since there's no navigation library
 * in this scaffold (same reasoning as [com.rrx.app.crash.CrashCountdownActivity]).
 * `DriveSection` launches this only while [com.rrx.coresensing.DriveSensingService]
 * is already running. */
@AndroidEntryPoint
class DriveModeActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RrxTheme(darkTheme = true) {
                DriveModeScreen()
            }
        }
    }

    companion object {
        fun intentFor(context: Context): Intent = Intent(context, DriveModeActivity::class.java)
    }
}
