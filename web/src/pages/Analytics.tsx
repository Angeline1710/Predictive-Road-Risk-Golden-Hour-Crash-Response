import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, recentLatencyP95 } from "../lib/api";
import type { AnalyticsSummary, ChannelBucket } from "../lib/api";
import { Shell } from "../components/Shell";
import { useThemeStore } from "../lib/theme";
import { downloadCsv, exportSvgAsPng, resolveToken } from "../lib/exportChart";
import type { HonestyFeed } from "../components/SystemHonestyBar";

const HONESTY_FEEDS: HonestyFeed[] = [
  { name: "weather", status: "down", ageLabel: "no API key configured" },
  { name: "sms gw", status: "healthy", ageLabel: "" },
];

const SINCE_OPTIONS = [
  { hours: 24, label: "Last 24h" },
  { hours: 168, label: "Last 7d" },
  { hours: 720, label: "Last 30d" },
];

// ml/reports/risk_model_results.json -- static training-time evaluation,
// copied verbatim (like app/ml/risk_model.py's own BAND_THRESHOLDS), not
// re-read live, since this is a report artifact, not database state.
const RISK_MODEL_REPORT = {
  prAuc: 0.0836, prAucStd: 0.0077, rocAuc: 0.8410,
  precisionAtTop1Pct: 0.1442, liftAtTop1Pct: 15.85,
  brier: 0.008647,
  bands: [
    { band: "Low", threshold: 0.00326, observedRate: 0.0009 },
    { band: "Moderate", threshold: 0.01366, observedRate: 0.0056 },
    { band: "High", threshold: 0.05330, observedRate: 0.0266 },
    { band: "Severe", threshold: null as number | null, observedRate: 0.1145 },
  ],
};

// ml/MODELS.md §2.5 -- synthetic-holdout crash-detection evaluation.
// Explicitly NOT live operational data: MODELS.md's own §0 states these
// "figures are not evidence that [Model A] detects crashes" in the real
// world, and §6 states false-positive rate "is currently unmeasurable"
// operationally, because POST /alerts' `window.outcome` (cancelled/expired)
// is accepted but never persisted (app/services/alerts.py never reads it).
const DETECTION_SYNTHETIC = {
  fpPer100DrivingHoursDegraded: 0.00,
  fpPer100DrivingHoursFull: 1.36,
  targetFpPer100DrivingHours: 2.0,
};

function fmtSeconds(s: number | null): string {
  if (s === null) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  if (s < 3600) return `${(s / 60).toFixed(1)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}
function fmtPct(p: number | null): string {
  return p === null ? "—" : `${p.toFixed(1)}%`;
}

/** UX-APPFLOW.md §24. Light theme by default (forced on mount, same
 * setTheme-in-useEffect pattern LiveOperations.tsx uses to force dark).
 * All six panels pull from a single new endpoint, GET /analytics/summary
 * (app/api/analytics.py) -- except Detection quality and Risk model
 * performance, which have no live database source and are static
 * constants instead (see the comments above), rendered with heavy
 * labelling rather than presented as live numbers. */
export function Analytics() {
  const setTheme = useThemeStore((s) => s.setTheme);
  const [sinceHours, setSinceHours] = useState(24);

  useEffect(() => {
    setTheme("light"); // Analytics defaults light -- UX-APPFLOW.md §24
  }, [setTheme]);

  const query = useQuery({
    queryKey: ["analytics", "summary", sinceHours],
    queryFn: () => api.analyticsSummary(sinceHours),
  });

  return (
    <Shell
      title="Analytics"
      active="analytics"
      role="ANALYST"
      honestyFeeds={HONESTY_FEEDS}
      latencyMs={recentLatencyP95() ?? undefined}
      latencyLabel="API p95 (client)"
    >
      <div style={{ height: "100%", overflowY: "auto", padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <p style={{ fontFamily: "var(--font-ui)", fontSize: 12, color: "var(--ink-muted)", maxWidth: 640, margin: 0 }}>
            Built to be screenshotted into government presentations -- every chart uses only the risk-band and
            system tokens already used elsewhere in this dashboard, and stays legible in greyscale.
          </p>
          <select
            value={sinceHours}
            onChange={(e) => setSinceHours(Number(e.target.value))}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", color: "var(--ink-primary)", fontFamily: "var(--font-ui)", fontSize: 13, padding: "6px 10px" }}
          >
            {SINCE_OPTIONS.map((o) => (
              <option key={o.hours} value={o.hours}>{o.label}</option>
            ))}
          </select>
        </div>

        {query.isLoading && <p style={{ color: "var(--ink-muted)", fontFamily: "var(--font-ui)" }}>Loading…</p>}
        {query.isError && (
          <p style={{ color: "var(--flare-500)", fontFamily: "var(--font-ui)" }}>
            Could not reach the API — {(query.error as Error).message}
          </p>
        )}

        {query.data && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <ResponsePanel data={query.data} />
            <ChannelMixPanel data={query.data} />
            <GoldenHourPanel data={query.data} />
            <DetectionQualityPanel />
            <RiskModelPanel />
            <CoveragePanel data={query.data} />
          </div>
        )}
      </div>
    </Shell>
  );
}

function PanelFrame({
  title, note, onExportPng, onExportCsv, children,
}: {
  title: string;
  note?: string;
  onExportPng: () => void;
  onExportCsv: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontFamily: "var(--font-ui)", fontWeight: 600, fontSize: 12, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink-secondary)" }}>
          {title}
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          <ExportButton label="PNG" onClick={onExportPng} />
          <ExportButton label="CSV" onClick={onExportCsv} />
        </div>
      </div>
      {children}
      {note && <p style={{ fontSize: 11, color: "var(--ink-muted)", marginTop: 8, marginBottom: 0 }}>{note}</p>}
    </div>
  );
}

function ExportButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{ background: "var(--paper-300)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", color: "var(--ink-primary)", fontFamily: "var(--font-ui)", fontSize: 11, padding: "3px 8px", cursor: "pointer" }}
    >
      {label}
    </button>
  );
}

// -- 1. Response performance -------------------------------------------------

function ResponsePanel({ data }: { data: AnalyticsSummary }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { response_latency: lat } = data;
  const w = 460, h = 200, padL = 10, padB = 24, padT = 10;
  const chartW = w - padL * 2, chartH = h - padT - padB;
  const maxCount = Math.max(1, ...lat.histogram.map((b) => b.count));
  const barGap = 6;
  const barW = (chartW - barGap * (lat.histogram.length - 1)) / lat.histogram.length;
  const sodium = resolveToken("--sodium-500") || "#E8971C";
  const flare = resolveToken("--flare-500") || "#E03131";
  const muted = resolveToken("--ink-muted") || "#6B7369";

  // Which bucket p95 falls in, for the marker rule.
  const p95BucketIdx = lat.p95_s === null ? -1 : lat.histogram.findIndex((b) => b.le_s === null || lat.p95_s! < b.le_s);

  return (
    <PanelFrame
      title="Response performance"
      note="Crash → acknowledgement latency: device impact time to the simulated PM-RAHAT gateway's synchronous ack (POST /sim/gateway/mode's OK/SLOW/TIMEOUT/REJECT). Not a real government dispatch response time -- there is no live ERSS-112 link in this deployment."
      onExportPng={() => svgRef.current && exportSvgAsPng(svgRef.current, "response-performance.png")}
      onExportCsv={() => downloadCsv(
        "response-performance.csv",
        ["bucket", "le_seconds", "count"],
        lat.histogram.map((b) => [b.label, b.le_s ?? "inf", b.count]),
      )}
    >
      <svg ref={svgRef} viewBox={`0 0 ${w} ${h}`} width="100%" style={{ overflow: "visible" }}>
        {lat.histogram.map((b, i) => {
          const x = padL + i * (barW + barGap);
          const barH = (b.count / maxCount) * chartH;
          const y = padT + chartH - barH;
          return (
            <g key={b.label}>
              <rect x={x} y={y} width={barW} height={Math.max(0, barH)} fill={sodium} opacity={0.85} />
              <text x={x + barW / 2} y={h - 6} textAnchor="middle" fontFamily="var(--font-ui)" fontSize={9} fill={muted}>{b.label}</text>
              {b.count > 0 && (
                <text x={x + barW / 2} y={y - 3} textAnchor="middle" fontFamily="var(--font-telemetry)" fontSize={10} fill="var(--ink-primary)">{b.count}</text>
              )}
            </g>
          );
        })}
        {p95BucketIdx >= 0 && (
          <g>
            <line
              x1={padL + p95BucketIdx * (barW + barGap) + barW / 2}
              y1={padT}
              x2={padL + p95BucketIdx * (barW + barGap) + barW / 2}
              y2={padT + chartH}
              stroke={flare}
              strokeWidth={1.5}
              strokeDasharray="4 3"
            />
            <text x={padL + p95BucketIdx * (barW + barGap) + barW / 2 + 4} y={padT + 10} fontFamily="var(--font-telemetry)" fontSize={9} fill={flare}>p95</text>
          </g>
        )}
      </svg>
      <div style={{ display: "flex", gap: 20, marginTop: 6 }}>
        <Stat label="p50" value={fmtSeconds(lat.p50_s)} />
        <Stat label="p95" value={fmtSeconds(lat.p95_s)} color="var(--flare-500)" />
        <Stat label="p99" value={fmtSeconds(lat.p99_s)} />
        <Stat label="n" value={String(lat.n)} />
      </div>
    </PanelFrame>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontFamily: "var(--font-ui)", fontSize: 10, color: "var(--ink-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
      <div style={{ fontFamily: "var(--font-telemetry)", fontSize: 16, color: color ?? "var(--ink-primary)" }}>{value}</div>
    </div>
  );
}

// -- 2. Channel mix -----------------------------------------------------------

function ChannelMixPanel({ data }: { data: AnalyticsSummary }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const buckets: ChannelBucket[] = data.channel_mix;
  const w = 460, h = 200, padL = 10, padB = 24, padT = 10;
  const chartW = w - padL * 2, chartH = h - padT - padB;
  const maxTotal = Math.max(1, ...buckets.map((b) => b.data + b.sms + b.manual_sos));
  const barGap = 6;
  const barW = buckets.length > 0 ? (chartW - barGap * (buckets.length - 1)) / buckets.length : chartW;
  const dataColor = resolveToken("--risk-low") || "#3E8C74";
  const sosColor = resolveToken("--flare-500") || "#E03131";
  const smsColor = resolveToken("--sodium-500") || "#E8971C";
  const muted = resolveToken("--ink-muted") || "#6B7369";

  return (
    <PanelFrame
      title="Channel mix"
      note="DATA vs SMS vs MANUAL_SOS, bucketed by hour of ingest. SMS stacks on top -- it's the differentiator (PRD §16.2 step 5: alert still lands over airplane mode)."
      onExportPng={() => svgRef.current && exportSvgAsPng(svgRef.current, "channel-mix.png")}
      onExportCsv={() => downloadCsv(
        "channel-mix.csv",
        ["hour", "data", "sms", "manual_sos"],
        buckets.map((b) => [b.hour, b.data, b.sms, b.manual_sos]),
      )}
    >
      {buckets.length === 0 ? (
        <EmptyChart height={h} />
      ) : (
        <svg ref={svgRef} viewBox={`0 0 ${w} ${h}`} width="100%" style={{ overflow: "visible" }}>
          {buckets.map((b, i) => {
            const x = padL + i * (barW + barGap);
            const dataH = (b.data / maxTotal) * chartH;
            const sosH = (b.manual_sos / maxTotal) * chartH;
            const smsH = (b.sms / maxTotal) * chartH;
            let yCursor = padT + chartH;
            const dataY = yCursor - dataH; yCursor = dataY;
            const sosY = yCursor - sosH; yCursor = sosY;
            const smsY = yCursor - smsH;
            return (
              <g key={b.hour}>
                <rect x={x} y={dataY} width={barW} height={dataH} fill={dataColor} />
                <rect x={x} y={sosY} width={barW} height={sosH} fill={sosColor} />
                <rect x={x} y={smsY} width={barW} height={smsH} fill={smsColor} />
                <text x={x + barW / 2} y={h - 6} textAnchor="middle" fontFamily="var(--font-ui)" fontSize={9} fill={muted}>
                  {new Date(b.hour).toLocaleTimeString("en-IN", { hour: "2-digit", hour12: false })}
                </text>
              </g>
            );
          })}
        </svg>
      )}
      <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
        <Legend color={dataColor} label="DATA" />
        <Legend color={sosColor} label="MANUAL_SOS" />
        <Legend color={smsColor} label="SMS" />
      </div>
    </PanelFrame>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 10, height: 10, background: color, display: "inline-block", borderRadius: 2 }} />
      <span style={{ fontFamily: "var(--font-ui)", fontSize: 11, color: "var(--ink-secondary)" }}>{label}</span>
    </div>
  );
}

function EmptyChart({ height }: { height: number }) {
  return (
    <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-muted)", fontFamily: "var(--font-ui)", fontSize: 12 }}>
      No alerts in this window.
    </div>
  );
}

// -- 3. Golden Hour compliance ------------------------------------------------

function GoldenHourPanel({ data }: { data: AnalyticsSummary }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gh = data.golden_hour;
  const w = 460, h = 140;
  const cols = [
    { label: "within 60 min", value: gh.within_60min_pct },
    { label: "within 30 min", value: gh.within_30min_pct },
    { label: "within 15 min", value: gh.within_15min_pct },
  ];
  const colW = w / cols.length;
  const sodium = resolveToken("--sodium-500") || "#E8971C";
  const primary = resolveToken("--ink-primary") || "#141A16";
  const muted = resolveToken("--ink-muted") || "#6B7369";

  return (
    <PanelFrame
      title="Golden Hour compliance"
      note="Same simulated-gateway caveat as Response performance above: this measures ingest → simulated dispatch acknowledgement, not a real field response time. No historical trend is stored yet, so the spec's sparkline is omitted rather than faked with invented history."
      onExportPng={() => svgRef.current && exportSvgAsPng(svgRef.current, "golden-hour-compliance.png")}
      onExportCsv={() => downloadCsv(
        "golden-hour-compliance.csv",
        ["threshold", "pct", "n"],
        cols.map((c) => [c.label, c.value ?? "", gh.n]),
      )}
    >
      <svg ref={svgRef} viewBox={`0 0 ${w} ${h}`} width="100%">
        {cols.map((c, i) => (
          <g key={c.label}>
            <text x={i * colW + colW / 2} y={70} textAnchor="middle" fontFamily="var(--font-telemetry)" fontSize={34} fill={c.value === null ? muted : sodium}>
              {fmtPct(c.value)}
            </text>
            <text x={i * colW + colW / 2} y={100} textAnchor="middle" fontFamily="var(--font-ui)" fontSize={11} fill={primary}>
              {c.label}
            </text>
          </g>
        ))}
        <text x={w / 2} y={130} textAnchor="middle" fontFamily="var(--font-ui)" fontSize={10} fill={muted}>n = {gh.n} alerts with a recorded dispatch ack</text>
      </svg>
    </PanelFrame>
  );
}

// -- 4. Detection quality ------------------------------------------------------

function DetectionQualityPanel() {
  const svgRef = useRef<SVGSVGElement>(null);
  const w = 460, h = 160;
  const muted = resolveToken("--ink-muted") || "#6B7369";
  const primary = resolveToken("--ink-primary") || "#141A16";
  const flare = resolveToken("--flare-500") || "#E03131";
  const sodium = resolveToken("--sodium-500") || "#E8971C";

  return (
    <PanelFrame
      title="Detection quality"
      note="Cancel rate per 100 drive-hours is not computable from live data: POST /alerts' cancel signal (window.outcome) is accepted but never persisted (app/services/alerts.py never reads it), and no drive-hours telemetry exists. The numbers below are Model A's synthetic-holdout evaluation, not live operational data -- ml/MODELS.md's own caution against reading them as real-world evidence applies here unchanged."
      onExportPng={() => svgRef.current && exportSvgAsPng(svgRef.current, "detection-quality.png")}
      onExportCsv={() => downloadCsv(
        "detection-quality.csv",
        ["metric", "value", "source"],
        [
          ["live cancel rate / 100 drive-hours", "not available", "no cancel signal persisted"],
          ["synthetic FP / 100 driving-h (degraded gate)", DETECTION_SYNTHETIC.fpPer100DrivingHoursDegraded, "ml/reports (synthetic holdout)"],
          ["synthetic FP / 100 driving-h (full gate)", DETECTION_SYNTHETIC.fpPer100DrivingHoursFull, "ml/reports (synthetic holdout)"],
          ["target", DETECTION_SYNTHETIC.targetFpPer100DrivingHours, "UX-APPFLOW.md §24"],
        ],
      )}
    >
      <svg ref={svgRef} viewBox={`0 0 ${w} ${h}`} width="100%">
        <text x={w / 2} y={36} textAnchor="middle" fontFamily="var(--font-telemetry)" fontSize={22} fill={muted}>Not available (live)</text>
        <text x={w / 2} y={56} textAnchor="middle" fontFamily="var(--font-ui)" fontSize={11} fill={muted}>no cancel signal is persisted server-side yet</text>

        <line x1={30} y1={78} x2={w - 30} y2={78} stroke="var(--border)" />

        <text x={30} y={100} fontFamily="var(--font-ui)" fontSize={11} fill={primary}>Synthetic holdout (Model A, ml/reports) --</text>
        <text x={30} y={118} fontFamily="var(--font-telemetry)" fontSize={13} fill={sodium}>degraded gate {DETECTION_SYNTHETIC.fpPer100DrivingHoursDegraded.toFixed(2)}</text>
        <text x={220} y={118} fontFamily="var(--font-telemetry)" fontSize={13} fill={sodium}>full gate {DETECTION_SYNTHETIC.fpPer100DrivingHoursFull.toFixed(2)}</text>
        <text x={30} y={138} fontFamily="var(--font-telemetry)" fontSize={12} fill={flare}>target: {DETECTION_SYNTHETIC.targetFpPer100DrivingHours.toFixed(1)} FP/100 driving-h</text>
      </svg>
    </PanelFrame>
  );
}

// -- 5. Risk model performance -------------------------------------------------

function RiskModelPanel() {
  const svgRef = useRef<SVGSVGElement>(null);
  const w = 460, h = 230, padL = 60, padR = 10, padT = 60, padB = 24;
  const chartW = w - padL - padR, chartH = h - padT - padB;
  const maxRate = Math.max(...RISK_MODEL_REPORT.bands.map((b) => b.observedRate)) * 1.15;
  const barGap = 10;
  const barW = (chartW - barGap * (RISK_MODEL_REPORT.bands.length - 1)) / RISK_MODEL_REPORT.bands.length;
  const bandColors: Record<string, string> = {
    Low: resolveToken("--risk-low") || "#3E8C74",
    Moderate: resolveToken("--risk-mod") || "#D9A227",
    High: resolveToken("--risk-high") || "#D9622B",
    Severe: resolveToken("--risk-severe") || "#B4232F",
  };
  const muted = resolveToken("--ink-muted") || "#6B7369";
  const primary = resolveToken("--ink-primary") || "#141A16";

  return (
    <PanelFrame
      title="Risk model performance"
      note="risk_model_v1, from ml/reports/risk_model_results.json (spatial-blocked cross-validation) -- static training-time evaluation, not recomputed from live traffic. Calibration shown as the 4 trained bands' observed crash rate, not a continuous reliability curve (no per-prediction outcome log exists to build one from)."
      onExportPng={() => svgRef.current && exportSvgAsPng(svgRef.current, "risk-model-performance.png")}
      onExportCsv={() => downloadCsv(
        "risk-model-performance.csv",
        ["metric", "value"],
        [
          ["PR-AUC", RISK_MODEL_REPORT.prAuc], ["PR-AUC std", RISK_MODEL_REPORT.prAucStd],
          ["ROC-AUC", RISK_MODEL_REPORT.rocAuc], ["Precision@top-1%", RISK_MODEL_REPORT.precisionAtTop1Pct],
          ["Lift@top-1%", RISK_MODEL_REPORT.liftAtTop1Pct], ["Brier", RISK_MODEL_REPORT.brier],
          ...RISK_MODEL_REPORT.bands.map((b) => [`${b.band} observed rate`, b.observedRate]),
        ],
      )}
    >
      <svg ref={svgRef} viewBox={`0 0 ${w} ${h}`} width="100%">
        <text x={0} y={16} fontFamily="var(--font-telemetry)" fontSize={12} fill={primary}>PR-AUC {RISK_MODEL_REPORT.prAuc.toFixed(4)}</text>
        <text x={120} y={16} fontFamily="var(--font-telemetry)" fontSize={12} fill={primary}>Brier {RISK_MODEL_REPORT.brier.toFixed(4)}</text>
        <text x={240} y={16} fontFamily="var(--font-telemetry)" fontSize={12} fill={primary}>P@top1% {(RISK_MODEL_REPORT.precisionAtTop1Pct * 100).toFixed(1)}%</text>
        <text x={370} y={16} fontFamily="var(--font-telemetry)" fontSize={12} fill={primary}>Lift {RISK_MODEL_REPORT.liftAtTop1Pct.toFixed(1)}×</text>
        <text x={0} y={36} fontFamily="var(--font-ui)" fontSize={10} fill={muted}>Band-level observed crash rate (calibration)</text>

        {RISK_MODEL_REPORT.bands.map((b, i) => {
          const x = padL + i * (barW + barGap);
          const barH = (b.observedRate / maxRate) * chartH;
          const y = padT + chartH - barH;
          return (
            <g key={b.band}>
              <rect x={x} y={y} width={barW} height={barH} fill={bandColors[b.band]} />
              <text x={x + barW / 2} y={y - 4} textAnchor="middle" fontFamily="var(--font-telemetry)" fontSize={10} fill="var(--ink-primary)">
                {(b.observedRate * 100).toFixed(2)}%
              </text>
              <text x={x + barW / 2} y={h - 6} textAnchor="middle" fontFamily="var(--font-ui)" fontSize={10} fill={muted}>{b.band}</text>
            </g>
          );
        })}
        <line x1={padL} y1={padT + chartH} x2={w - padR} y2={padT + chartH} stroke="var(--border)" />
      </svg>
    </PanelFrame>
  );
}

// -- 6. Coverage ----------------------------------------------------------------

function CoveragePanel({ data }: { data: AnalyticsSummary }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const c = data.coverage;
  const w = 460, h = 180;
  const primary = resolveToken("--ink-primary") || "#141A16";
  const muted = resolveToken("--ink-muted") || "#6B7369";
  const sodium = resolveToken("--sodium-500") || "#E8971C";

  const stats = [
    { label: "Devices active/total", value: `${c.devices_active} / ${c.devices_total}` },
    { label: "Network monitored", value: `${c.network_km.toLocaleString()} km` },
    { label: "Segments", value: c.segment_count.toLocaleString() },
    { label: "Responder units", value: c.responder_unit_count.toLocaleString() },
  ];

  return (
    <PanelFrame
      title="Coverage"
      note={`Districts: ${c.districts.join(", ") || "none"} (${c.districts.length}). A choropleth needs 2+ districts to be a meaningful map -- this corridor is a single-district extraction (MVP-PLAN.md §2③), so the count is shown as a stat instead of a fabricated one-polygon map.`}
      onExportPng={() => svgRef.current && exportSvgAsPng(svgRef.current, "coverage.png")}
      onExportCsv={() => downloadCsv(
        "coverage.csv",
        ["metric", "value"],
        [...stats.map((s) => [s.label, s.value]), ["districts", c.districts.join("; ")]],
      )}
    >
      <svg ref={svgRef} viewBox={`0 0 ${w} ${h}`} width="100%">
        {stats.map((s, i) => {
          const col = i % 2, row = Math.floor(i / 2);
          const x = col * (w / 2) + 10, y = row * 90 + 30;
          return (
            <g key={s.label}>
              <text x={x} y={y} fontFamily="var(--font-telemetry)" fontSize={22} fill={sodium}>{s.value}</text>
              <text x={x} y={y + 18} fontFamily="var(--font-ui)" fontSize={11} fill={muted}>{s.label}</text>
            </g>
          );
        })}
        <text x={10} y={170} fontFamily="var(--font-ui)" fontSize={11} fill={primary}>{c.districts.length} district{c.districts.length === 1 ? "" : "s"} covered: {c.districts.join(", ") || "—"}</text>
      </svg>
    </PanelFrame>
  );
}
