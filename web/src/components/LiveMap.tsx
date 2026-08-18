import { useEffect, useRef } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { renderToStaticMarkup } from "react-dom/server";
import type { AlertSummary, RiskPoint } from "../lib/api";
import { RISK_BANDS, SEVERITY_BANDS, bandKeyFromApi, severityKeyFromApi, type RiskBandKey } from "../lib/bands";
import { MilestoneMarker, type MarkerZoomTier } from "./MilestoneMarker";
import { isUnacknowledged } from "./IncidentCard";

// NH-45/Chengalpattu corridor -- etl/extract_corridor.py's CORRIDOR_BBOX,
// the only area the ETL has populated with real segment data.
export const CORRIDOR_CENTER: [number, number] = [12.85, 80.165];
export const CORRIDOR_BOUNDS: [[number, number], [number, number]] = [
  [12.75, 80.05],
  [12.95, 80.28],
];

function zoomTierFor(zoom: number): MarkerZoomTier {
  if (zoom < 9) return "dot";
  if (zoom < 11) return "compact";
  return "full";
}

function markerIcon(subLabel: string, band: (typeof RISK_BANDS)["low"], zoomTier: MarkerZoomTier, pulsing: boolean, selected: boolean) {
  const html = renderToStaticMarkup(
    <MilestoneMarker band={band} subLabel={subLabel} zoomTier={zoomTier} pulsing={pulsing} selected={selected} />
  );
  const w = zoomTier === "full" ? 40 : zoomTier === "compact" ? 32 : 12;
  const h = zoomTier === "full" ? 52 : zoomTier === "compact" ? 42 : 12;
  return L.divIcon({ html, className: "milestone-marker-icon", iconSize: [w, h], iconAnchor: [w / 2, h] });
}

function ZoomWatcher({ onZoom }: { onZoom: (z: number) => void }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  return null;
}

function FlyToSelected({ target }: { target: [number, number] | null }) {
  const map = useMap();
  const done = useRef<string | null>(null);
  useEffect(() => {
    if (!target) return;
    const key = target.join(",");
    if (done.current === key) return;
    done.current = key;
    map.flyTo(target, Math.max(map.getZoom(), 13), { duration: 0.28 });
  }, [target, map]);
  return null;
}

export interface LiveMapProps {
  riskSegments: RiskPoint[];
  showRisk: boolean;
  incidents: AlertSummary[];
  selectedUuid: string | null;
  onSelectIncident: (uuid: string) => void;
  zoom: number;
  onZoomChange: (z: number) => void;
}

/** UX-APPFLOW.md §21.1. The custom "Milestone tile style" (bitumen-000
 * ground, no POIs/buildings/landuse) described there is a bespoke vector
 * basemap this MVP doesn't have a tile-serving pipeline for -- CARTO's
 * dark, label-free basemap is used as an honest approximation, same as
 * /risk/route and /risk/tiles being left unimplemented rather than faked
 * (app/api/risk.py's own docstring). Real data: the risk overlay and
 * incident markers, both wired to the live backend. */
export function LiveMap({ riskSegments, showRisk, incidents, selectedUuid, onSelectIncident, zoom, onZoomChange }: LiveMapProps) {
  const zoomTier = zoomTierFor(zoom);
  const selected = incidents.find((i) => i.alert_uuid === selectedUuid) ?? null;

  return (
    <MapContainer
      center={CORRIDOR_CENTER}
      zoom={13}
      style={{ height: "100%", width: "100%", background: "var(--bitumen-000)" }}
      zoomControl={false}
    >
      <ZoomWatcher onZoom={onZoomChange} />
      <FlyToSelected target={selected ? [selected.lat, selected.lon] : null} />

      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
        attribution="&copy; OpenStreetMap contributors &copy; CARTO"
        maxZoom={19}
      />

      {showRisk &&
        riskSegments.map((seg) => {
          const bandKey: RiskBandKey = bandKeyFromApi(seg.band);
          const spec = RISK_BANDS[bandKey];
          const positions = seg.geometry.map(([lon, lat]) => [lat, lon] as [number, number]);
          return (
            <Polyline
              key={seg.segment_id}
              positions={positions}
              pathOptions={{
                color: spec.cssVar,
                weight: spec.mapStroke,
                opacity: 0.6,
                dashArray: spec.pattern === "dashed" ? "4 3" : undefined,
              }}
            >
              <Popup>
                <div style={{ fontFamily: "var(--font-telemetry)", fontSize: 12 }}>
                  <div>
                    SEG {seg.segment_id} — {spec.letter} {seg.score.toFixed(2)}
                  </div>
                  <div style={{ color: "var(--ink-muted)" }}>{seg.district ?? "unknown district"}</div>
                  {seg.top_factors.slice(0, 3).map((f) => (
                    <div key={f}>{f}</div>
                  ))}
                </div>
              </Popup>
            </Polyline>
          );
        })}

      {incidents.map((inc) => {
        const spec = SEVERITY_BANDS[severityKeyFromApi(inc.severity)];
        const label = zoomTier === "dot" ? "" : new Date(inc.occurred_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
        return (
          <Marker
            key={inc.alert_uuid}
            position={[inc.lat, inc.lon]}
            icon={markerIcon(label, spec, zoomTier, isUnacknowledged(inc.status), inc.alert_uuid === selectedUuid)}
            eventHandlers={{ click: () => onSelectIncident(inc.alert_uuid) }}
          />
        );
      })}
    </MapContainer>
  );
}
