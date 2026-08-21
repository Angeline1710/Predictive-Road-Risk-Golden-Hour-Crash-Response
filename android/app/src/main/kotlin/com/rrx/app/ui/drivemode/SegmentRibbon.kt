package com.rrx.app.ui.drivemode

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rrx.app.ui.theme.Bitumen200
import com.rrx.app.ui.theme.Highway300
import com.rrx.app.ui.theme.InkInverse
import com.rrx.app.ui.theme.Paper100
import com.rrx.app.ui.theme.Sodium500
import com.rrx.app.ui.theme.TypeCaption
import com.rrx.app.ui.theme.TypeOverline

private const val RIBBON_CELL_COUNT = 10

/**
 * UX-APPFLOW.md §13's Segment Ribbon. [nearby] is already sorted
 * nearest-first by [DriveModeViewModel]; this takes the closest
 * [RIBBON_CELL_COUNT] and renders one cell per segment, band colour plus
 * the NFR-A3-mandated letter token (never colour alone). `● LIVE` /
 * `◐ CACHED` reflects [isLive] -- when the last `/risk/bbox` refetch
 * failed or has gone stale, the ribbon still shows the last-known data
 * (per §13's "never mistake stale risk for live risk," it says so rather
 * than hiding it), just labelled honestly.
 */
@Composable
fun SegmentRibbon(nearby: List<NearbySegment>, isLive: Boolean, modifier: Modifier = Modifier) {
    val cells = nearby.take(RIBBON_CELL_COUNT)
    val nextNotable = nearby.firstOrNull { it.band.isNotable }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(Bitumen200)
            .padding(12.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("ROAD AHEAD", style = TypeOverline, color = Paper100.copy(alpha = 0.7f))
            Text(
                if (isLive) "● LIVE" else "◐ CACHED",
                style = TypeOverline,
                color = if (isLive) Highway300 else Sodium500,
            )
        }

        if (cells.isEmpty()) {
            Text(
                "No risk data for this area yet",
                style = TypeCaption,
                color = Paper100.copy(alpha = 0.6f),
                modifier = Modifier.padding(top = 8.dp),
            )
        } else {
            // Manual equal-width division via BoxWithConstraints rather than
            // Modifier.weight() -- avoids relying on RowScope.weight()
            // resolving unambiguously in this Compose Foundation version,
            // and the per-cell width is trivial to compute anyway since
            // there's a fixed, known cell count.
            BoxWithConstraints(modifier = Modifier.fillMaxWidth().padding(top = 8.dp).height(28.dp)) {
                val cellWidth = maxWidth / cells.size
                Row {
                    cells.forEach { seg ->
                        Box(
                            modifier = Modifier.width(cellWidth).height(28.dp).padding(horizontal = 1.dp).background(seg.band.color),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(seg.band.letter, style = TypeCaption, color = InkInverse, textAlign = TextAlign.Center)
                        }
                    }
                }
            }

            if (nextNotable != null) {
                Text(
                    "%.1f km · %s · %s".format(
                        nextNotable.distanceM / 1000.0,
                        nextNotable.band.name.lowercase().replaceFirstChar { it.uppercase() },
                        nextNotable.risk.topFactors.joinToString(", "),
                    ),
                    style = TypeCaption,
                    color = Paper100,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }
    }
}
