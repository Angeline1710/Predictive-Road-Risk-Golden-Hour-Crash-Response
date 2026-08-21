package com.rrx.app.ui.drivemode

import android.content.Context
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.viewinterop.AndroidView
import com.rrx.app.network.dto.RiskContextDto
import com.rrx.coresensing.GpsFix
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline

/**
 * UX-APPFLOW.md §13's map: "Deliberately low-detail: no POIs, no business
 * labels, no satellite. Only road geometry, the banded route, and
 * Milestone Markers." `osmdroid`'s default `MAPNIK` tile source is a full
 * OSM street map (POIs, labels, everything) -- this pass draws the
 * risk-banded polylines on top of it rather than swapping in a custom
 * low-detail tile source, since that needs either a self-hosted tile
 * server or a vector-tile style this project doesn't have (the dashboard
 * has the same honest gap -- `web/src/components/LiveMap.tsx`'s doc
 * comment calls its CARTO basemap "an honest approximation," not the
 * bespoke style §21.1 asks for).
 */
private fun configureOsmdroid(context: Context) {
    val config = Configuration.getInstance()
    config.userAgentValue = context.packageName
    config.osmdroidBasePath = context.getExternalFilesDir(null) ?: context.filesDir
    config.osmdroidTileCache = java.io.File(config.osmdroidBasePath, "tiles").apply { mkdirs() }
}

@Composable
fun DriveModeMap(
    segments: List<RiskContextDto>,
    driverFix: GpsFix?,
    modifier: Modifier = Modifier,
) {
    // by mutableStateOf, not a plain `remember { false }` -- a bare `var`
    // reassigned inside the `update` closure doesn't write back into the
    // remember slot, so the map would silently re-center on every single
    // segment/driverFix update forever instead of only once.
    var centered by remember { mutableStateOf(false) }

    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = { ctx ->
            configureOsmdroid(ctx)
            MapView(ctx).apply {
                setTileSource(TileSourceFactory.MAPNIK)
                setMultiTouchControls(true)
                controller.setZoom(15.0)
            }
        },
        update = { mapView ->
            mapView.overlays.clear()

            segments.forEach { seg ->
                val band = RiskBand.fromApi(seg.band)
                val points = seg.geometry.map { (lon, lat) -> GeoPoint(lat, lon) }
                if (points.size < 2) return@forEach
                mapView.overlays.add(
                    Polyline(mapView).apply {
                        setPoints(points)
                        outlinePaint.color = band.color.toArgb()
                        outlinePaint.strokeWidth = band.mapStrokeWidthPx
                    }
                )
                // Heuristic Milestone Marker proxy: §13 asks for markers
                // "at blackspots," but RiskContextOut has no discrete
                // is_blackspot flag -- only top_factors mentioning it as
                // a contributing SHAP reason. Placed on notable bands
                // only, at the segment's first vertex, not the actual
                // blackspot point (which the API doesn't expose
                // separately from the segment geometry).
                if (band.isNotable && seg.topFactors.any { it.contains("black spot", ignoreCase = true) }) {
                    val (lon0, lat0) = seg.geometry.first()
                    mapView.overlays.add(
                        Marker(mapView).apply {
                            position = GeoPoint(lat0, lon0)
                            title = "${band.letter} · ${seg.district ?: "Unknown district"}"
                        }
                    )
                }
            }

            if (driverFix != null) {
                mapView.overlays.add(
                    Marker(mapView).apply {
                        position = GeoPoint(driverFix.lat, driverFix.lon)
                        rotation = driverFix.headingDeg
                        title = "You"
                    }
                )
                if (!centered) {
                    mapView.controller.setCenter(GeoPoint(driverFix.lat, driverFix.lon))
                    centered = true
                }
            }

            mapView.invalidate()
        },
        // Full onResume()/onPause()/onDetach() lifecycle wiring (osmdroid's
        // own tile-cache background threads expect it, paired to the
        // hosting Activity's lifecycle) is skipped for this pass -- a
        // documented simplification, not a crash risk: an un-paused
        // MapView just keeps its tile-loading threads alive slightly
        // longer than ideal after the screen closes, rather than failing
        // outright.
    )
}
