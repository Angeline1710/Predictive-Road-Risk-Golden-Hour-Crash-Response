package com.rrx.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// UX-APPFLOW.md §6.1's three-voice system: Display (Fraunces), Interface
// (Inter), Telemetry (IBM Plex Mono). The web dashboard loads these as
// real webfonts (web/index.html); this scaffold can't embed the binary
// .ttf/.otf assets Compose needs for res/font/, so each family falls back
// to the platform default until real font files are added to the project;
// an honest gap, not a silent substitution pretending to be final.
val DisplayFontFamily = FontFamily.Default // TODO: Fraunces variable font
val InterfaceFontFamily = FontFamily.Default // TODO: Inter variable font
val TelemetryFontFamily = FontFamily.Monospace // closest built-in stand-in for IBM Plex Mono

// UX-APPFLOW.md §6.2's type scale -- the subset this scaffold's one real
// screen (HomeScreen) actually uses.
val RrxTypography = Typography(
    headlineMedium = TextStyle(
        fontFamily = DisplayFontFamily,
        fontWeight = FontWeight.SemiBold,
        fontSize = 28.sp, // type-heading-1
        lineHeight = (28 * 1.25).sp,
    ),
    titleMedium = TextStyle(
        fontFamily = InterfaceFontFamily,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp, // type-heading-3
        lineHeight = (18 * 1.4).sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = InterfaceFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 17.sp, // type-body-lg
        lineHeight = (17 * 1.55).sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = InterfaceFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp, // type-body
        lineHeight = (15 * 1.6).sp,
    ),
    labelSmall = TextStyle(
        fontFamily = TelemetryFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp, // type-telemetry-sm
        lineHeight = (12 * 1.4).sp,
    ),
)
