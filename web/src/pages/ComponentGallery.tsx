import { useEffect, useState } from "react";
import { MilestoneMarker } from "../components/MilestoneMarker";
import { SegmentRibbon, type RibbonSegment } from "../components/SegmentRibbon";
import { GoldenHourDial } from "../components/GoldenHourDial";
import { ChannelBadge } from "../components/ChannelBadge";
import { SimulationSeal } from "../components/SimulationSeal";
import { TraceSparkline, type TraceSample } from "../components/TraceSparkline";
import { SystemHonestyBar } from "../components/SystemHonestyBar";
import { RISK_BANDS, SEVERITY_BANDS } from "../lib/bands";
import { useThemeStore } from "../lib/theme";

const RIBBON_SEGMENTS: RibbonSegment[] = [
  { segmentId: 101, band: RISK_BANDS.low, score: 0.12, distanceKm: 0.0 },
  { segmentId: 102, band: RISK_BANDS.low, score: 0.18, distanceKm: 0.5 },
  { segmentId: 103, band: RISK_BANDS.mod, score: 0.41, distanceKm: 1.0 },
  { segmentId: 104, band: RISK_BANDS.high, score: 0.63, distanceKm: 1.5, topFactors: ["curvature", "night", "heavy_share"] },
  { segmentId: 105, band: RISK_BANDS.severe, score: 0.88, distanceKm: 2.0, topFactors: ["black_spot", "no_median", "speed"] },
  { segmentId: 106, band: RISK_BANDS.severe, score: 0.84, distanceKm: 2.5 },
  { segmentId: 107, band: RISK_BANDS.high, score: 0.58, distanceKm: 3.0 },
  { segmentId: 108, band: RISK_BANDS.mod, score: 0.37, distanceKm: 3.5 },
  { segmentId: 109, band: RISK_BANDS.mod, score: 0.33, distanceKm: 4.0 },
  { segmentId: 110, band: RISK_BANDS.low, score: 0.15, distanceKm: 4.5 },
];

function synthTrace(): TraceSample[] {
  const samples: TraceSample[] = [];
  for (let t = -8; t <= 4; t += 0.1) {
    let g = 1.0 + Math.sin(t * 0.7) * 0.15;
    if (t > -0.15 && t < 0.35) {
      g += Math.exp(-Math.pow((t - 0.05) / 0.06, 2)) * 7.5;
    }
    samples.push({ t: Math.round(t * 100) / 100, g: Math.max(0, g) });
  }
  return samples;
}
const TRACE_SAMPLES = synthTrace();

/** Signature-component scaffold check (UX-APPFLOW.md §7). Assembles all
 * seven components against representative data so the design system can
 * be verified end to end before the real Live Operations view (task #15)
 * replaces this page. */
export function ComponentGallery() {
  const setTheme = useThemeStore((s) => s.setTheme);
  const [elapsed, setElapsed] = useState(2478);

  useEffect(() => {
    setTheme("dark");
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, [setTheme]);

  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1, padding: 32, display: "flex", flexDirection: "column", gap: 40 }}>
        <header>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, color: "var(--ink-primary)", margin: 0 }}>
            Signature components
          </h1>
          <p style={{ color: "var(--ink-muted)", marginTop: 4 }}>UX-APPFLOW.md §7 — scaffold verification</p>
        </header>

        <section>
          <h2 style={sectionHeading}>7.1 Milestone Marker</h2>
          <div style={{ display: "flex", gap: 24, alignItems: "flex-end" }}>
            {(Object.keys(RISK_BANDS) as (keyof typeof RISK_BANDS)[]).map((k) => (
              <MilestoneMarker key={k} band={RISK_BANDS[k]} subLabel="0.84" />
            ))}
            <MilestoneMarker band={SEVERITY_BANDS.critical} subLabel="02:41" pulsing />
            <MilestoneMarker band={RISK_BANDS.high} subLabel="0.63" selected />
            <MilestoneMarker band={RISK_BANDS.severe} subLabel="" zoomTier="dot" />
          </div>
        </section>

        <section>
          <h2 style={sectionHeading}>7.2 Segment Ribbon</h2>
          <SegmentRibbon segments={RIBBON_SEGMENTS} currentIndex={2} variant="dashboard" />
        </section>

        <section>
          <h2 style={sectionHeading}>7.3 Golden Hour Dial</h2>
          <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
            <GoldenHourDial elapsedSeconds={elapsed} />
            <GoldenHourDial elapsedSeconds={elapsed} size="row" />
            <GoldenHourDial elapsedSeconds={3180} />
            <GoldenHourDial elapsedSeconds={4324} />
          </div>
        </section>

        <section>
          <h2 style={sectionHeading}>7.4 Channel Badge</h2>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <ChannelBadge channel="DATA" />
            <ChannelBadge channel="SMS" hasTrace />
            <ChannelBadge channel="SMS" hasTrace={false} />
            <ChannelBadge channel="MANUAL_SOS" />
          </div>
        </section>

        <section>
          <h2 style={sectionHeading}>7.5 Simulation Seal</h2>
          <div style={{ maxWidth: 420 }}>
            <SimulationSeal ticketId="SIM-2026-0814-004417" assignmentLine="Assigned · Chengalpattu GH Trauma · 6.2 km" />
          </div>
        </section>

        <section>
          <h2 style={sectionHeading}>7.6 Trace Sparkline</h2>
          <div style={{ maxWidth: 640 }}>
            <TraceSparkline samples={TRACE_SAMPLES} stillMoving />
          </div>
        </section>
      </div>

      <SystemHonestyBar
        feeds={[
          { name: "weather", status: "healthy", ageLabel: "4m" },
          { name: "traffic", status: "healthy", ageLabel: "2m" },
          { name: "imd", status: "degraded", ageLabel: "3h STALE" },
          { name: "sms gw", status: "healthy", ageLabel: "" },
        ]}
        latencyMs={218}
        deviceCount={1284}
      />
    </div>
  );
}

const sectionHeading: React.CSSProperties = {
  fontFamily: "var(--font-ui)",
  fontSize: 13,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "var(--ink-muted)",
  marginBottom: 12,
};
