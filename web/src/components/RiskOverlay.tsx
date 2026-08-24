import { Polyline, Popup } from "react-leaflet";
import type { RiskPoint } from "../lib/api";
import { RISK_BANDS, bandKeyFromApi, type RiskBandKey } from "../lib/bands";

/** The risk-segment-as-stroked-polyline rendering shared by LiveMap.tsx
 * (incident view, risk as one of several layers) and RiskMap.tsx (analyst
 * view, risk is the whole point) -- extracted so the two views can't drift
 * into two different renderings of the same RiskContextOut shape. */
export function RiskOverlay({ segments }: { segments: RiskPoint[] }) {
  return (
    <>
      {segments.map((seg) => {
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
    </>
  );
}
