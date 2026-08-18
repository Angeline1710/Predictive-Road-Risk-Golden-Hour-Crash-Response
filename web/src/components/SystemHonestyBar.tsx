export type FeedStatus = "healthy" | "degraded" | "down";

export interface HonestyFeed {
  name: string;
  status: FeedStatus;
  /** Data age, already formatted (e.g. "4m", "3h STALE") -- age is what
   * actually tells an operator whether to trust the map, not a vague
   * "connected" (§7.7). */
  ageLabel: string;
}

export interface SystemHonestyBarProps {
  feeds: HonestyFeed[];
  latencyMs?: number;
  /** Defaults to the UX-APPFLOW.md §7.7 mockup's literal label. Live
   * Operations passes something more precise ("API p95 (client)") since
   * what it feeds in is round-trip time observed from the browser, not
   * server-side ingest latency -- conflating the two is exactly the kind
   * of overclaim this bar exists to prevent. */
  latencyLabel?: string;
  deviceCount?: number;
  onFeedClick?: (feed: HonestyFeed) => void;
  className?: string;
}

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

const STATUS_GLYPH: Record<FeedStatus, string> = { healthy: "●", degraded: "◐", down: "○" };
const STATUS_COLOR: Record<FeedStatus, string> = {
  healthy: "var(--highway-300)",
  degraded: "var(--sodium-500)",
  down: "var(--flare-500)",
};

/** Persistent 32px strip along the bottom of the ops dashboard showing the
 * live health of every dependency (UX-APPFLOW.md §7.7) -- direct
 * expression of principle P2. An operator who doesn't know the weather
 * feed is 3 hours stale will over-trust a risk score. */
export function SystemHonestyBar({
  feeds,
  latencyMs,
  latencyLabel = "INGEST p95",
  deviceCount,
  onFeedClick,
  className,
}: SystemHonestyBarProps) {
  return (
    <div
      className={className}
      style={{
        height: 32,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        background: "var(--bitumen-100)",
        borderTop: "1px solid var(--border)",
        fontFamily: "var(--font-telemetry)",
        fontSize: 11,
        color: "var(--ink-secondary)",
        gap: 16,
        overflowX: "auto",
        whiteSpace: "nowrap",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {feeds.map((f) => (
          <button
            key={f.name}
            onClick={() => onFeedClick?.(f)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: "none",
              border: "none",
              padding: 0,
              cursor: onFeedClick ? "pointer" : "default",
              font: "inherit",
              color: "inherit",
            }}
          >
            <span style={{ color: STATUS_COLOR[f.status] }}>{STATUS_GLYPH[f.status]}</span>
            <span style={{ textTransform: "uppercase" }}>{f.name}</span>
            <span style={{ color: "var(--ink-muted)" }}>{f.ageLabel}</span>
          </button>
        ))}

        {/* permanently present, cannot be hidden -- v1 has no live gateway */}
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--flare-500)" }}>
          <span aria-hidden>◆</span>
          <span>GATEWAY SIMULATED</span>
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16, color: "var(--ink-muted)" }}>
        {latencyMs !== undefined && (
          <span>
            {latencyLabel} {formatLatency(latencyMs)}
          </span>
        )}
        {deviceCount !== undefined && <span>{deviceCount.toLocaleString("en-IN")} DEVICES</span>}
      </div>
    </div>
  );
}
