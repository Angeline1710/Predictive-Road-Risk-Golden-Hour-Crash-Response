import type { AlertSummary } from "../lib/api";
import { GoldenHourDial } from "./GoldenHourDial";
import { ChannelBadge } from "./ChannelBadge";
import { HeadlightSweep } from "./HeadlightSweep";
import { SEVERITY_BANDS, severityKeyFromApi } from "../lib/bands";

export type DispatchPhase = "awaiting" | "dispatched" | "closed" | "failed";

/** UX-APPFLOW.md §21.2's three dispatch-progress states, mapped from
 * AlertStatus. The backend has no separate "operator acknowledged" action
 * yet (models/alert.py's ACKNOWLEDGED represents the gateway acknowledging
 * receipt, not a dashboard action), so pre-dispatch statuses read as
 * "awaiting" and DISPATCHED/ACKNOWLEDGED/CLOSED read as resolved -- an
 * honest MVP simplification of the full three-state strip. */
export function dispatchPhase(status: string): DispatchPhase {
  switch (status) {
    case "DISPATCHED":
    case "ACKNOWLEDGED":
      return "dispatched";
    case "CLOSED":
      return "closed";
    case "FAILED":
    case "CANCELLED":
      return "failed";
    default:
      return "awaiting";
  }
}

export function isUnacknowledged(status: string): boolean {
  return dispatchPhase(status) === "awaiting";
}

export interface IncidentCardProps {
  alert: AlertSummary;
  selected?: boolean;
  onSelect?: () => void;
  /** UX-APPFLOW.md §22: "Opened from a card." A separate affordance from
   * `onSelect` (which highlights the map marker) rather than making the
   * whole card navigate -- a card click here still means "show me this on
   * the map," the same behaviour already verified in Live Operations;
   * opening the full detail view is a deliberate second action, not an
   * overload of the first. */
  onOpenDetail?: () => void;
}

/** One incident in the Live Operations rail (UX-APPFLOW.md §21.2). */
export function IncidentCard({ alert, selected = false, onSelect, onOpenDetail }: IncidentCardProps) {
  const severity = SEVERITY_BANDS[severityKeyFromApi(alert.severity)];
  const phase = dispatchPhase(alert.status);
  const elapsedSeconds = (Date.now() - new Date(alert.occurred_at).getTime()) / 1000;

  const [road, district] = (alert.landmark ?? "Unmatched location").split(",").map((s) => s.trim());

  return (
    <div
      onClick={onSelect}
      style={{
        position: "relative",
        overflow: "hidden",
        display: "flex",
        gap: 12,
        padding: 12,
        background: "var(--bitumen-100)",
        borderRadius: "var(--radius-md)",
        borderLeft: `4px solid ${severity.cssVar}`,
        outline: selected ? "2px solid var(--sodium-500)" : "none",
        cursor: onSelect ? "pointer" : "default",
        transition: "background var(--motion-fast) var(--ease-standard)",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bitumen-200)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bitumen-100)")}
    >
      <GoldenHourDial elapsedSeconds={elapsedSeconds} size="row" />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span
            style={{
              fontFamily: "var(--font-ui)",
              fontWeight: 600,
              fontSize: 18,
              color: severity.cssVar,
            }}
          >
            {alert.severity}
          </span>
          <ChannelBadge channel={alert.channel} hasTrace={alert.has_trace} />
        </div>

        <div style={{ marginTop: 4, fontFamily: "var(--font-ui)", fontSize: 15, color: "var(--ink-primary)" }}>
          {road}
          {district && <span style={{ color: "var(--ink-muted)" }}> · {district}</span>}
        </div>
        <div style={{ fontFamily: "var(--font-telemetry)", fontSize: 12, color: "var(--ink-muted)" }}>
          {alert.lat.toFixed(5)} {alert.lon.toFixed(5)}
        </div>

        <div style={{ marginTop: 6, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div style={{ position: "relative", overflow: "hidden", borderRadius: "var(--radius-sm)", flex: 1, minWidth: 0 }}>
            {phase === "awaiting" && <HeadlightSweep />}
            <StatusStrip phase={phase} ticketId={alert.ticket_id} />
          </div>
          {onOpenDetail && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpenDetail();
              }}
              style={{
                flexShrink: 0,
                background: "transparent",
                border: "none",
                color: "var(--sodium-500)",
                fontFamily: "var(--font-ui)",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                padding: "2px 0",
              }}
            >
              Details →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusStrip({ phase, ticketId }: { phase: DispatchPhase; ticketId: string | null }) {
  if (phase === "dispatched") {
    return (
      <span style={strip("var(--highway-300)")}>
        ✓ DISPATCHED{ticketId ? ` · ${ticketId}` : ""}
      </span>
    );
  }
  if (phase === "closed") {
    return <span style={strip("var(--ink-muted)")}>● CLOSED</span>;
  }
  if (phase === "failed") {
    return <span style={strip("var(--flare-500)")}>○ DISPATCH FAILED</span>;
  }
  return <span style={strip("var(--sodium-500)")}>⚠ AWAITING DISPATCH</span>;
}

function strip(color: string): React.CSSProperties {
  return {
    display: "inline-block",
    fontFamily: "var(--font-ui)",
    fontSize: 12,
    fontWeight: 500,
    color,
    padding: "2px 0",
  };
}
