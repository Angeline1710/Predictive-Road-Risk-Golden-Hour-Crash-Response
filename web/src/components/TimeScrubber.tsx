export interface TimeScrubberProps {
  /** Minutes in the past; 0 = live. */
  minutesAgo: number;
  onChange: (minutesAgo: number) => void;
  scrubbedLabel: string;
}

/** Bottom-centre 24h replay control (UX-APPFLOW.md §21.1). Dragging
 * re-queries `/v1/risk/bbox?at=...` for that hour (Model B is a
 * segment×hour model, so this is a real recomputation, not a canned
 * animation) and client-filters the incident list to what had occurred by
 * that point -- both against data the backend actually has. */
export function TimeScrubber({ minutesAgo, onChange, scrubbedLabel }: TimeScrubberProps) {
  const isLive = minutesAgo === 0;

  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        bottom: 12,
        transform: "translateX(-50%)",
        zIndex: 500,
        display: "flex",
        alignItems: "center",
        gap: 10,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: "8px 12px",
        boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
      }}
    >
      <button
        onClick={() => onChange(0)}
        style={{
          fontFamily: "var(--font-ui)",
          fontWeight: 600,
          fontSize: 11,
          letterSpacing: "0.06em",
          color: isLive ? "var(--ink-inverse)" : "var(--sodium-500)",
          background: isLive ? "var(--sodium-500)" : "transparent",
          border: "1px solid var(--sodium-500)",
          borderRadius: "var(--radius-sm)",
          padding: "4px 8px",
          cursor: "pointer",
        }}
      >
        LIVE
      </button>
      <input
        type="range"
        min={0}
        max={1440}
        step={15}
        value={minutesAgo}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: 220 }}
        aria-label="Replay time, minutes ago"
      />
      <span style={{ fontFamily: "var(--font-telemetry)", fontSize: 12, color: "var(--ink-muted)", minWidth: 70 }}>
        {isLive ? "now" : `−${scrubbedLabel}`}
      </span>
    </div>
  );
}
