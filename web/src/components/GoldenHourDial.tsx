export interface GoldenHourDialProps {
  /** Seconds since the crash was confirmed. Negative or zero renders a
   * full, untouched dial. */
  elapsedSeconds: number;
  size?: "detail" | "row";
  className?: string;
}

const GOLDEN_HOUR_S = 3600;

function arcColor(remainingS: number): string {
  const remainingMin = remainingS / 60;
  if (remainingMin > 40) return "var(--sodium-500)";
  if (remainingMin > 20) return "var(--sodium-600)";
  if (remainingMin > 10) return "var(--risk-high)";
  return "var(--flare-500)";
}

function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

/** The 60-minute radial countdown that begins the instant a crash is
 * confirmed (UX-APPFLOW.md §7.3) -- the product's namesake. One dial per
 * incident, never used decoratively. At zero it flips to a count-up rather
 * than a failure state: the golden hour passing is not a system error. */
export function GoldenHourDial({ elapsedSeconds, size = "detail", className }: GoldenHourDialProps) {
  const diameter = size === "detail" ? 160 : 72;
  const stroke = 6;
  const r = diameter / 2 - stroke;
  const cx = diameter / 2;
  const cy = diameter / 2;
  const circumference = 2 * Math.PI * r;

  const remaining = GOLDEN_HOUR_S - elapsedSeconds;
  const overtime = remaining <= 0;
  const critical = !overtime && remaining < 600;

  const fraction = overtime ? 1 : Math.min(1, Math.max(0, elapsedSeconds / GOLDEN_HOUR_S));
  const dashOffset = circumference * (1 - fraction);
  const color = overtime ? "var(--bitumen-400)" : arcColor(remaining);

  const ticks =
    size === "detail"
      ? Array.from({ length: 60 }, (_, i) => {
          const angle = (i / 60) * 2 * Math.PI - Math.PI / 2;
          const outer = r + stroke / 2 + 2;
          const inner = outer - 4;
          const elapsedTick = !overtime && i < (elapsedSeconds / 60);
          return {
            i,
            x1: cx + inner * Math.cos(angle),
            y1: cy + inner * Math.sin(angle),
            x2: cx + outer * Math.cos(angle),
            y2: cy + outer * Math.sin(angle),
            color: elapsedTick ? "var(--bitumen-400)" : "var(--sodium-400)",
          };
        })
      : [];

  return (
    <div
      className={className}
      style={{
        position: "relative",
        width: diameter,
        height: diameter,
        animation: critical ? "dial-heartbeat 1s ease-in-out infinite" : undefined,
      }}
      role="img"
      aria-label={overtime ? `${formatClock(-remaining)} elapsed past golden hour` : `${formatClock(remaining)} remaining`}
    >
      <svg width={diameter} height={diameter}>
        {ticks.map((t) => (
          <line key={t.i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} stroke={t.color} strokeWidth={1} />
        ))}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bitumen-300)" strokeWidth={stroke} opacity={0.3} />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-telemetry)",
            fontSize: size === "detail" ? 32 : diameter * 0.24,
            color: overtime ? "var(--ink-muted)" : "var(--ink-primary)",
            lineHeight: 1,
          }}
        >
          {overtime ? `+${formatClock(-remaining)}` : formatClock(remaining)}
        </span>
        {size === "detail" && (
          <span
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: 11,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
              marginTop: 4,
            }}
          >
            {overtime ? "Elapsed" : "Remaining"}
          </span>
        )}
      </div>
    </div>
  );
}
