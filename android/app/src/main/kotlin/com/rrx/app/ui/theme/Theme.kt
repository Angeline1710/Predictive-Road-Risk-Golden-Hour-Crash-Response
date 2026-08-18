package com.rrx.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

// UX-APPFLOW.md §28's light-default / [data-theme="dark"] blocks, mapped
// onto Material3's ColorScheme. Drive Mode and the crash path use dark by
// default per §20; this scaffold's HomeScreen follows the system setting.
private val RrxLightColors = lightColorScheme(
    primary = Sodium500,
    onPrimary = Bitumen050,
    background = Paper000,
    surface = Paper100,
    onBackground = Bitumen100,
    onSurface = Bitumen100,
    error = Flare500,
)

private val RrxDarkColors = darkColorScheme(
    primary = Sodium500,
    onPrimary = Bitumen050,
    background = Bitumen050,
    surface = Bitumen100,
    onBackground = Paper100,
    onSurface = Paper100,
    error = Flare500,
)

@Composable
fun RrxTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) RrxDarkColors else RrxLightColors,
        typography = RrxTypography,
        content = content,
    )
}
