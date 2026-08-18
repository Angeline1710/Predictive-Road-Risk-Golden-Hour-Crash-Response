import { useMemo, useState } from "react";

export interface TraceSample {
  /** Seconds relative to impact; contract spans -8s to +4s. */
  t: number;
  /** Acceleration magnitude in g. */
  g: number;
}

export interface TraceSparklineProps {
  samples: TraceSample[];
  /** Detection threshold in g -- STAGE_A_G from ml/common/config.py. */
  thresholdG?: number;
  /** Whether the device kept moving after impact -- a secondary-collision
   * risk cue (§7.6). */
  stillMoving?: boolean;
  height?: number;
  className?: string;
}

const T_MIN = -8;
const T_MAX = 4;

/** The 12-second accelerometer trace rendered as a filled area chart
 * (UX-APPFLOW.md §7.6) -- the evidence. Converts "our model says this was
 * a crash" into something a human can verify with their own eyes in under
 * a second. */
export function TraceSparkline({
  samples,
  thresholdG = 4.0,
  stillMoving = false,
  height = 100,
  className,
}: TraceSparklineProps) {
  const [hoverT, setHoverT] = useState<number | null>(null);
  const width = 600; // viewBox units; caller stretches via CSS width:100%

  const maxG = useMemo(() => Math.max(thresholdG * 1.2, ...samples.map((s) => s.g), 1), [samples, thresholdG]);

  const xOf = (t: number) => ((t - T_MIN) / (T_MAX - T_MIN)) * width;
  const yOf = (g: number) => height - (g / maxG) * height;

  const sorted = useMemo(() => [...samples].sort((a, b) => a.t - b.t), [samples]);

  const linePath = sorted.map((s, i) => `${i === 0 ? "M" : "L"} ${xOf(s.t)} ${yOf(s.g)}`).join(" ");
  const areaPath =
    sorted.length > 0
      ? `${linePath} L ${xOf(sorted[sorted.length - 1].t)} ${height} L ${xOf(sorted[0].t)} ${height} Z`
      : "";

  const impactX = xOf(0);
  const thresholdY = yOf(thresholdG);
  const peakG = sorted.length > 0 ? Math.max(...sorted.map((s) => s.g)) : 0;

  const hoverSample =
    hoverT === null
      ? null
      : sorted.reduce((closest, s) => (Math.abs(s.t - hoverT) < Math.abs(closest.t - hoverT) ? s : closest), sorted[0]);

  return (
    <div className={className} style={{ position: "relative", width: "100%", height }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const frac = (e.clientX - rect.left) / rect.width;
          setHoverT(T_MIN + frac * (T_MAX - T_MIN));
        }}
        onMouseLeave={() => setHoverT(null)}
      >
        <defs>
          <linearGradient id="trace-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--sodium-500)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--sodium-500)" stopOpacity={0} />
          </linearGradient>
        </defs>

        {/* post-impact secondary-collision tint */}
        {stillMoving && (
          <rect x={impactX} y={0} width={width - impactX} height={height} fill="var(--flare-500)" opacity={0.06} />
        )}

        {/* 4g detection threshold */}
        <line x1={0} y1={thresholdY} x2={width} y2={thresholdY} stroke="var(--bitumen-500)" strokeWidth={1} strokeDasharray="4 3" />
        <text x={width - 4} y={thresholdY - 4} textAnchor="end" fontFamily="var(--font-telemetry)" fontSize={10} fill="var(--bitumen-500)">
          {thresholdG.toFixed(1)} g
        </text>

        {areaPath && <path d={areaPath} fill="url(#trace-fill)" />}
        {linePath && <path d={linePath} fill="none" stroke="var(--sodium-500)" strokeWidth={1.5} />}

        {/* impact moment */}
        <line x1={impactX} y1={0} x2={impactX} y2={height} stroke="var(--flare-500)" strokeWidth={1} />
        <text x={impactX + 4} y={12} fontFamily="var(--font-telemetry)" fontSize={10} fill="var(--flare-500)">
          T=0 · {peakG.toFixed(1)}g
        </text>

        {hoverSample && (
          <line x1={xOf(hoverSample.t)} y1={0} x2={xOf(hoverSample.t)} y2={height} stroke="var(--ink-muted)" strokeWidth={1} strokeDasharray="2 2" />
        )}
      </svg>

      {hoverSample && (
        <div
          style={{
            position: "absolute",
            top: 4,
            right: 4,
            fontFamily: "var(--font-telemetry)",
            fontSize: 11,
            color: "var(--ink-primary)",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "2px 6px",
            pointerEvents: "none",
          }}
        >
          {hoverSample.t.toFixed(2)}s · {hoverSample.g.toFixed(2)}g
        </div>
      )}
    </div>
  );
}
