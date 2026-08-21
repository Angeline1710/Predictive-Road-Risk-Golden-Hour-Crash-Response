package com.rrx.app.ui.drivemode

import androidx.compose.ui.graphics.Color
import com.rrx.app.ui.theme.RiskHigh
import com.rrx.app.ui.theme.RiskLow
import com.rrx.app.ui.theme.RiskMod
import com.rrx.app.ui.theme.RiskNone
import com.rrx.app.ui.theme.RiskSevere

/**
 * UX-APPFLOW.md §4.7's four bands, mirroring `web/src/lib/bands.ts`'s
 * `RiskBandKey`/`bandKeyFromApi` -- same mapping, same "API returns
 * capitalized strings, parse defensively" discipline, different language.
 * NFR-A3's full triple encoding (hue + hatch pattern + letter token) isn't
 * complete here: the letter token and hue are real, but rendering a hatch
 * fill pattern on an `osmdroid` `Polyline` or inside a Compose `Canvas`
 * cell needs a `Shader`/`PathEffect` this pass didn't build -- stroke
 * width still varies by band (mirroring `BandSpec.mapStroke`), which is a
 * partial, not full, substitute for the missing pattern.
 */
enum class RiskBand(val letter: String, val color: Color, val mapStrokeWidthPx: Float) {
    LOW("L", RiskLow, 3f),
    MODERATE("M", RiskMod, 4f),
    HIGH("H", RiskHigh, 5f),
    SEVERE("S", RiskSevere, 6f),
    NONE("–", RiskNone, 2f);

    val isNotable: Boolean get() = this == HIGH || this == SEVERE

    companion object {
        fun fromApi(band: String): RiskBand = when (band.lowercase()) {
            "low" -> LOW
            "moderate" -> MODERATE
            "high" -> HIGH
            "severe" -> SEVERE
            else -> NONE
        }
    }
}
