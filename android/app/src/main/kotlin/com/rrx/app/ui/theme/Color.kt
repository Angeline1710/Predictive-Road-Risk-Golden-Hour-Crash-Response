package com.rrx.app.ui.theme

import androidx.compose.ui.graphics.Color

// Transcribed verbatim from web/src/styles/tokens.css, which is itself a
// verbatim transcription of UX-APPFLOW.md §28. Single source of truth: if
// this ever needs to change, change §28 first, then this file.

// Bitumen -- dark theme grounds
val Bitumen000 = Color(0xFF0A0F0D)
val Bitumen050 = Color(0xFF0E1512)
val Bitumen100 = Color(0xFF141C18)
val Bitumen200 = Color(0xFF1B241F)
val Bitumen300 = Color(0xFF24302A)
val Bitumen400 = Color(0xFF33413A)
val Bitumen500 = Color(0xFF475A50)

// Paper -- light theme grounds
val Paper000 = Color(0xFFFBFAF6)
val Paper100 = Color(0xFFF4F2EA)
val Paper200 = Color(0xFFEAE7DB)
val Paper300 = Color(0xFFDCD8C8)
val Paper400 = Color(0xFFC6C1AE)

// Sodium -- the signature accent
val Sodium200 = Color(0xFFFFE3B8)
val Sodium300 = Color(0xFFFFCC80)
val Sodium400 = Color(0xFFF5B14C)
val Sodium500 = Color(0xFFE8971C)
val Sodium600 = Color(0xFFC87C0D)
val Sodium700 = Color(0xFF94590A)

// Highway -- institutional green
val Highway300 = Color(0xFF5FBF95)
val Highway500 = Color(0xFF1F6B4A)
val Highway600 = Color(0xFF175339)
val Highway700 = Color(0xFF0F3A28)

// Risk band ramp -- semantic only, never decorative (UX-APPFLOW.md §4.7).
// Pair every use with the band's hatch pattern and letter token (NFR-A3);
// never read band identity from hue alone.
val RiskLow = Color(0xFF3E8C74)
val RiskMod = Color(0xFFD9A227)
val RiskHigh = Color(0xFFD9622B)
val RiskSevere = Color(0xFFB4232F)
val RiskNone = Color(0xFF4A554E)

// Flare -- critical, and deliberately scarce (UX-APPFLOW.md §4.8). Never
// the crash colour -- see §5.1, red means "the system failed", not "an
// emergency occurred".
val Flare500 = Color(0xFFE03131)
val Flare100 = Color(0xFFFFE0E0)
