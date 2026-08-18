import type { Channel } from "../lib/api";

export interface ChannelBadgeProps {
  channel: Channel;
  /** Only meaningful for the SMS channel: whether the sensor trace arrived
   * alongside the alert. When false, a PARTIAL sub-chip is shown so the
   * operator knows the record is incomplete, not that it's missing data
   * silently (§7.4). */
  hasTrace?: boolean;
  className?: string;
}

function SignalBarsGlyph({ color }: { color: string }) {
  return (
    <svg width={12} height={10} viewBox="0 0 12 10" aria-hidden>
      <rect x={0} y={6} width={2} height={4} fill={color} />
      <rect x={3.5} y={4} width={2} height={6} fill={color} />
      <rect x={7} y={2} width={2} height={8} fill={color} />
      <rect x={10} y={0} width={2} height={10} fill={color} />
    </svg>
  );
}

function EnvelopeGlyph({ color }: { color: string }) {
  return (
    <svg width={13} height={10} viewBox="0 0 13 10" aria-hidden>
      <rect x={0.5} y={0.5} width={12} height={9} rx={1} fill="none" stroke={color} strokeWidth={1} />
      <path d="M0.5 1 L6.5 6 L12.5 1" fill="none" stroke={color} strokeWidth={1} />
    </svg>
  );
}

function HandGlyph({ color }: { color: string }) {
  return (
    <svg width={10} height={11} viewBox="0 0 10 11" aria-hidden>
      <path
        d="M2 11V5a1 1 0 0 1 2 0v2M4 11V3a1 1 0 0 1 2 0v3M6 11V4a1 1 0 0 1 2 0v3M8 10V6a1 1 0 0 1 2 0v2c0 1.7-1.3 3-3 3H4c-1.1 0-1.7-.4-2.3-1L0 8"
        fill="none"
        stroke={color}
        strokeWidth={1}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const CHANNEL_LABEL: Record<Channel, string> = {
  DATA: "DATA",
  SMS: "SMS",
  MANUAL_SOS: "SOS",
};

/** Three-state badge showing how an alert reached the system
 * (UX-APPFLOW.md §7.4). The delivery channel is the product's core
 * differentiator -- an SMS badge means this alert came from somewhere
 * with no data connectivity and would not exist in any other system. */
export function ChannelBadge({ channel, hasTrace = true, className }: ChannelBadgeProps) {
  const base = {
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    height: 22,
    padding: "0 8px",
    borderRadius: "var(--radius-sm)",
    fontFamily: "var(--font-ui)",
    fontSize: 11,
    letterSpacing: "0.06em",
    textTransform: "uppercase" as const,
  };

  let style: React.CSSProperties;
  let glyph: React.ReactNode;

  if (channel === "DATA") {
    style = { ...base, background: "var(--bitumen-300)", color: "var(--ink-secondary)" };
    glyph = <SignalBarsGlyph color="var(--ink-secondary)" />;
  } else if (channel === "SMS") {
    style = {
      ...base,
      background: "transparent",
      color: "var(--sodium-500)",
      border: "1.5px solid var(--sodium-500)",
    };
    glyph = <EnvelopeGlyph color="var(--sodium-500)" />;
  } else {
    style = { ...base, background: "var(--flare-500)", color: "var(--ink-inverse)" };
    glyph = <HandGlyph color="var(--ink-inverse)" />;
  }

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }} className={className}>
      <span style={style}>
        {glyph}
        {CHANNEL_LABEL[channel]}
      </span>
      {channel === "SMS" && !hasTrace && (
        <span
          style={{
            ...base,
            padding: "0 6px",
            background: "transparent",
            color: "var(--ink-muted)",
            border: "1px dashed var(--ink-muted)",
          }}
        >
          PARTIAL
        </span>
      )}
    </span>
  );
}
