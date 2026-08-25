import { useEffect, useMemo, useState } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { MapContainer, TileLayer } from "react-leaflet";
import { api, recentLatencyP95 } from "../lib/api";
import type { HeatCell, RiskPoint } from "../lib/api";
import { Shell } from "../components/Shell";
import { RiskOverlay } from "../components/RiskOverlay";
import { CORRIDOR_CENTER, CORRIDOR_BOUNDS } from "../components/LiveMap";
import { ConditionSimulator, isSimulated, LIVE_CONDITIONS, type SimulatedConditions } from "../components/ConditionSimulator";
import { SegmentRibbon, type RibbonSegment } from "../components/SegmentRibbon";
import { RiskHeatGrid } from "../components/RiskHeatGrid";
import { distanceToNearestVertexKm } from "../lib/geo";
import { RISK_BANDS, bandKeyFromApi } from "../lib/bands";
import type { HonestyFeed } from "../components/SystemHonestyBar";

const HONESTY_FEEDS: HonestyFeed[] = [
  { name: "weather", status: "down", ageLabel: "no API key configured" },
  { name: "sms gw", status: "healthy", ageLabel: "" },
];

// The corridor is Chengalpattu, Tamil Nadu -- fixed to IST regardless of the
// analyst's own browser timezone, so "23:00" on the slider always means
// 23:00 at the road, not 23:00 wherever the dashboard happens to be open.
function atParamFor(hour: number | null): string | undefined {
  if (hour === null) return undefined;
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${String(hour).padStart(2, "0")}:00:00+05:30`;
}

type SortKey = "score" | "segment_id" | "district";

/** UX-APPFLOW.md §23, analyst view. Distinct from Live Operations
 * (LiveOperations.tsx): no incident rail, and the condition simulator is
 * the point rather than an afterthought. Corridor mode is real
 * (2026-08-25): the visible segments ordered by straight-line distance
 * from the corridor's own centre point (the same nearest-vertex proxy
 * android's DriveModeViewModel uses, not a true route-km marker -- see
 * lib/geo.ts) as a full-width Segment Ribbon, plus a real 24h x 7d
 * heat-grid for whichever segment is selected, batch-scored server-side
 * in one call (GET /risk/heatgrid). Comparison mode stays disabled: this
 * isn't "not ingested yet," it's that no real, sub-district-geolocatable
 * MoRTH-iRAD/SaveLIFE-ZFC blackspot dataset exists anywhere in this
 * project or was ever obtained -- PRD.md's own open question Q6 flags
 * this as unresolved, and every accident dataset actually on hand
 * (tn_road_accident_dataset_original.csv) is whole-district annual
 * totals with no sub-district location at all. Building Comparison mode
 * against that would mean fabricating blackspot placements, which this
 * project's honesty principle rules out -- so the button stays disabled
 * with the real reason, same posture as LayerControl.tsx's Weather/
 * Traffic/Blackspots toggles. */
export function RiskMap() {
  const [conditions, setConditions] = useState<SimulatedConditions>(LIVE_CONDITIONS);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [corridorMode, setCorridorMode] = useState(false);
  const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["risk", "bbox", "analyst", conditions],
    queryFn: () =>
      api.riskBbox(CORRIDOR_BOUNDS[0][0], CORRIDOR_BOUNDS[0][1], CORRIDOR_BOUNDS[1][0], CORRIDOR_BOUNDS[1][1], {
        limit: 1000,
        at: atParamFor(conditions.hour),
        weather: conditions.weather ?? undefined,
        visibility: conditions.visibility ?? undefined,
        trafficDensity: conditions.trafficDensity ?? undefined,
      }),
    refetchInterval: isSimulated(conditions) ? false : 30_000,
  });

  const segments = query.data ?? [];
  const sorted = useMemo(() => sortSegments(segments, sortKey, sortDir), [segments, sortKey, sortDir]);

  // Corridor mode's kilometre ruler: distance from the corridor's centre
  // point to each segment's nearest vertex -- straight-line, not a true
  // distance-along-the-route (lib/geo.ts's own doc comment covers why).
  const corridorSegments = useMemo(
    () =>
      [...segments]
        .map((s) => ({ ...s, distanceFromAnchorKm: distanceToNearestVertexKm(CORRIDOR_CENTER[0], CORRIDOR_CENTER[1], s.geometry) }))
        .sort((a, b) => a.distanceFromAnchorKm - b.distanceFromAnchorKm),
    [segments],
  );
  const effectiveSegmentId = selectedSegmentId ?? corridorSegments[0]?.segment_id ?? null;

  // Re-anchor the heat-grid selection to the nearest segment whenever the
  // prior selection scrolls out of the current viewport's segment set.
  useEffect(() => {
    if (selectedSegmentId != null && !corridorSegments.some((s) => s.segment_id === selectedSegmentId)) {
      setSelectedSegmentId(null);
    }
  }, [corridorSegments, selectedSegmentId]);

  const heatgridQuery = useQuery({
    queryKey: ["risk", "heatgrid", effectiveSegmentId],
    queryFn: () => api.riskHeatgrid(effectiveSegmentId!),
    enabled: corridorMode && effectiveSegmentId != null,
  });

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <Shell
      title="Risk Map"
      active="risk-map"
      role="ANALYST"
      honestyFeeds={HONESTY_FEEDS}
      latencyMs={recentLatencyP95() ?? undefined}
      latencyLabel="API p95 (client)"
    >
      <div style={{ display: "flex", height: "100%" }}>
        <ConditionSimulator value={conditions} onChange={setConditions} />

        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderBottom: "1px solid var(--border)",
              background: "var(--surface)",
            }}
          >
            <button
              onClick={() => setCorridorMode((v) => !v)}
              style={{
                background: corridorMode ? "var(--sodium-500)" : "var(--bitumen-200)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                color: corridorMode ? "var(--bitumen-000)" : "var(--ink-primary)",
                fontFamily: "var(--font-ui)",
                fontWeight: corridorMode ? 700 : 400,
                fontSize: 12,
                padding: "6px 10px",
                cursor: "pointer",
              }}
            >
              Corridor mode
            </button>
            <DisabledToolbarButton
              label="Comparison mode"
              reason="Comparison mode — not built: no real, geolocatable MoRTH/iRAD or SaveLIFE-ZFC blackspot dataset has ever been obtained for this corridor (PRD.md's own open question Q6) — every accident dataset on hand is whole-district annual totals, not placeable on a map"
            />
            {query.isFetching && (
              <span style={{ marginLeft: "auto", fontFamily: "var(--font-telemetry)", fontSize: 11, color: "var(--ink-muted)" }}>
                re-scoring…
              </span>
            )}
          </div>

          {corridorMode ? (
            <CorridorView
              corridorSegments={corridorSegments}
              selectedSegmentId={effectiveSegmentId}
              onSelectSegment={setSelectedSegmentId}
              heatgridQuery={heatgridQuery}
            />
          ) : (
            <>
              <div style={{ flex: "1 1 55%", minHeight: 0, position: "relative" }}>
                <MapContainer
                  center={CORRIDOR_CENTER}
                  zoom={13}
                  style={{ height: "100%", width: "100%", background: "var(--bitumen-000)" }}
                  zoomControl={false}
                >
                  <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
                    attribution="&copy; OpenStreetMap contributors &copy; CARTO"
                    maxZoom={19}
                  />
                  <RiskOverlay segments={segments} />
                </MapContainer>
                {query.isError && (
                  <div style={{ position: "absolute", top: 12, left: 12, zIndex: 500, background: "var(--surface)", border: "1px solid var(--flare-500)", borderRadius: "var(--radius-sm)", padding: "8px 12px", fontFamily: "var(--font-ui)", fontSize: 12, color: "var(--flare-500)" }}>
                    Could not reach the API — {(query.error as Error).message}
                  </div>
                )}
              </div>

              <TopNTable segments={sorted} sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}

type CorridorSegment = RiskPoint & { distanceFromAnchorKm: number };

function CorridorView({
  corridorSegments,
  selectedSegmentId,
  onSelectSegment,
  heatgridQuery,
}: {
  corridorSegments: CorridorSegment[];
  selectedSegmentId: number | null;
  onSelectSegment: (id: number) => void;
  heatgridQuery: UseQueryResult<HeatCell[], Error>;
}) {
  const ribbonSegments: RibbonSegment[] = corridorSegments.map((s) => ({
    segmentId: s.segment_id,
    band: RISK_BANDS[bandKeyFromApi(s.band)],
    score: s.score,
    topFactors: s.top_factors,
    distanceKm: s.distanceFromAnchorKm,
  }));
  const currentIndex = corridorSegments.findIndex((s) => s.segment_id === selectedSegmentId);
  const selected = currentIndex >= 0 ? corridorSegments[currentIndex] : null;

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: 20 }}>
      <div style={{ marginBottom: 8, fontFamily: "var(--font-ui)", fontSize: 11, color: "var(--ink-muted)" }}>
        {corridorSegments.length} segments, ordered by straight-line distance from the corridor centre (not a true route-km marker — see lib/geo.ts). Click a cell to inspect its 24h × 7d heat-grid.
      </div>

      {corridorSegments.length === 0 ? (
        <p style={{ color: "var(--ink-muted)", fontFamily: "var(--font-ui)", fontSize: 13 }}>No segments in view.</p>
      ) : (
        <SegmentRibbon
          segments={ribbonSegments}
          currentIndex={currentIndex >= 0 ? currentIndex : undefined}
          variant="dashboard"
          onSegmentClick={(s) => onSelectSegment(Number(s.segmentId))}
          className="corridor-ribbon"
        />
      )}

      <div style={{ marginTop: 40 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10 }}>
          <span style={{ fontFamily: "var(--font-ui)", fontWeight: 600, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
            Heat-grid
          </span>
          {selected && (
            <span style={{ fontFamily: "var(--font-telemetry)", fontSize: 12, color: "var(--ink-secondary)" }}>
              SEG {selected.segment_id} — {selected.district ?? selected.road_class ?? "unknown"}
            </span>
          )}
        </div>

        {heatgridQuery.isLoading && <p style={{ color: "var(--ink-muted)", fontFamily: "var(--font-ui)", fontSize: 13 }}>Scoring 168 hours…</p>}
        {heatgridQuery.isError && (
          <p style={{ color: "var(--flare-500)", fontFamily: "var(--font-ui)", fontSize: 13 }}>
            Could not reach the API — {heatgridQuery.error.message}
          </p>
        )}
        {heatgridQuery.data && <RiskHeatGrid cells={heatgridQuery.data} />}
      </div>
    </div>
  );
}

function DisabledToolbarButton({ label, reason }: { label: string; reason: string }) {
  return (
    <button
      disabled
      title={reason}
      style={{
        background: "var(--bitumen-200)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        color: "var(--ink-muted)",
        fontFamily: "var(--font-ui)",
        fontSize: 12,
        padding: "6px 10px",
        cursor: "not-allowed",
      }}
    >
      {label}
    </button>
  );
}

function sortSegments(segments: RiskPoint[], key: SortKey, dir: "asc" | "desc"): RiskPoint[] {
  const mul = dir === "asc" ? 1 : -1;
  return [...segments].sort((a, b) => {
    if (key === "score") return (a.score - b.score) * mul;
    if (key === "segment_id") return (a.segment_id - b.segment_id) * mul;
    return (a.district ?? "").localeCompare(b.district ?? "") * mul;
  });
}

function TopNTable({
  segments,
  sortKey,
  sortDir,
  onSort,
}: {
  segments: RiskPoint[];
  sortKey: SortKey;
  sortDir: "asc" | "desc";
  onSort: (key: SortKey) => void;
}) {
  function exportCsv() {
    const header = ["segment_id", "road_class", "district", "score", "band", "top_factors"];
    const rows = segments.map((s) => [
      s.segment_id, s.road_class ?? "", s.district ?? "", s.score.toFixed(4), s.band, s.top_factors.join("; "),
    ]);
    const csv = [header, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "risk-top-n.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ flex: "0 0 45%", minHeight: 0, borderTop: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 16px" }}>
        <span style={{ fontFamily: "var(--font-ui)", fontWeight: 600, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
          Top-N segments ({segments.length})
        </span>
        <button
          onClick={exportCsv}
          disabled={segments.length === 0}
          style={{
            background: "var(--bitumen-200)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
            color: "var(--ink-primary)", fontFamily: "var(--font-ui)", fontSize: 12, padding: "5px 10px",
            cursor: segments.length === 0 ? "not-allowed" : "pointer",
          }}
        >
          Export CSV
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 12px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-telemetry)", fontSize: 12 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--ink-muted)", borderBottom: "1px solid var(--border)" }}>
              <Th label="Segment" active={sortKey === "segment_id"} dir={sortDir} onClick={() => onSort("segment_id")} />
              <th style={{ padding: "6px 8px", fontWeight: 400 }}>Road</th>
              <Th label="District" active={sortKey === "district"} dir={sortDir} onClick={() => onSort("district")} />
              <Th label="Score" active={sortKey === "score"} dir={sortDir} onClick={() => onSort("score")} />
              <th style={{ padding: "6px 8px", fontWeight: 400 }}>Band</th>
              <th style={{ padding: "6px 8px", fontWeight: 400 }}>3-yr crashes</th>
              <th style={{ padding: "6px 8px", fontWeight: 400 }}>Blackspot</th>
              <th style={{ padding: "6px 8px", fontWeight: 400 }}>Top factors</th>
            </tr>
          </thead>
          <tbody>
            {segments.map((s) => {
              const spec = RISK_BANDS[bandKeyFromApi(s.band)];
              return (
                <tr key={s.segment_id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "6px 8px", color: "var(--ink-primary)" }}>{s.segment_id}</td>
                  <td style={{ padding: "6px 8px", color: "var(--ink-secondary)" }}>{s.road_class ?? "—"}</td>
                  <td style={{ padding: "6px 8px", color: "var(--ink-secondary)" }}>{s.district ?? "—"}</td>
                  <td style={{ padding: "6px 8px", color: "var(--ink-primary)" }}>{s.score.toFixed(3)}</td>
                  <td style={{ padding: "6px 8px", color: spec.cssVar, fontWeight: 700 }}>{spec.letter} {s.band}</td>
                  <td style={{ padding: "6px 8px", color: "var(--ink-muted)" }} title="hist_severe_3y is not populated from real crash history yet">No data</td>
                  <td style={{ padding: "6px 8px", color: "var(--ink-muted)" }} title="No MoRTH/iRAD blackspot list has been ingested (blackspots table is empty)">No data</td>
                  <td style={{ padding: "6px 8px", color: "var(--ink-secondary)", fontFamily: "var(--font-ui)" }}>
                    {s.top_factors.slice(0, 2).join(", ")}
                  </td>
                </tr>
              );
            })}
            {segments.length === 0 && (
              <tr>
                <td colSpan={8} style={{ padding: "16px 8px", color: "var(--ink-muted)", fontFamily: "var(--font-ui)" }}>
                  {"No segments in view."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ label, active, dir, onClick }: { label: string; active: boolean; dir: "asc" | "desc"; onClick: () => void }) {
  return (
    <th
      onClick={onClick}
      style={{ padding: "6px 8px", fontWeight: active ? 700 : 400, color: active ? "var(--ink-primary)" : "var(--ink-muted)", cursor: "pointer", userSelect: "none" }}
    >
      {label}{active ? (dir === "asc" ? " ▲" : " ▼") : ""}
    </th>
  );
}
