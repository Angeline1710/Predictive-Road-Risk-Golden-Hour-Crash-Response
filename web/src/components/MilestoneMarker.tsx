import type { BandSpec } from "../lib/bands";
import { BandPatternDefs, bandFill } from "./BandPatternDefs";

export type MarkerZoomTier = "full" | "compact" | "dot";

export interface MilestoneMarkerProps {
  /** Resolved band/severity spec -- caller maps risk band or incident
   * severity to a BandSpec via lib/bands.ts before rendering. */
  band: BandSpec;
  /** Risk score ("0.84") or incident time -- the small Telemetry-11 line
   * inside the body. */
  subLabel: string;
  zoomTier?: MarkerZoomTier;
  /** Unacknowledged incidents pulse a sodium-500 halo; stops the moment
   * the incident is acknowledged (§7.1). Never set for risk-map markers. */
  pulsing?: boolean;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}

/** The kilometre-stone map marker and incident token (UX-APPFLOW.md §7.1).
 * Replaces the generic teardrop pin -- the cap encodes risk band or
 * incident severity via hue + hatch pattern + letter token (NFR-A3 triple
 * encoding), never colour alone. */
export function MilestoneMarker({
  band,
  subLabel,
  zoomTier = "full",
  pulsing = false,
  selected = false,
  onClick,
  className,
}: MilestoneMarkerProps) {
  const fill = bandFill(band);

  if (zoomTier === "dot") {
    return (
      <span
        role={onClick ? "button" : undefined}
        onClick={onClick}
        className={className}
        style={{
          display: "inline-block",
          width: 12,
          height: 12,
          borderRadius: "50%",
          background: fill === "none" ? "transparent" : band.cssVar,
          border: fill === "none" ? "1.5px dashed var(--risk-none)" : "1px solid var(--bitumen-400)",
          cursor: onClick ? "pointer" : undefined,
        }}
        aria-label={`Risk band ${band.letter}`}
      />
    );
  }

  const w = zoomTier === "compact" ? 32 : 40;
  const h = zoomTier === "compact" ? 42 : 52;
  const scale = selected ? 1.15 : 1;

  return (
    <span
      role={onClick ? "button" : undefined}
      onClick={onClick}
      className={className}
      style={{
        position: "relative",
        display: "inline-block",
        width: w,
        height: h,
        transform: `scale(${scale})`,
        transformOrigin: "50% 100%",
        cursor: onClick ? "pointer" : undefined,
      }}
      aria-label={`${band.letter} band marker, ${subLabel}`}
    >
      {pulsing && (
        <span
          style={{
            position: "absolute",
            left: "50%",
            top: 10,
            width: 20,
            height: 20,
            marginLeft: -10,
            marginTop: -10,
            borderRadius: "50%",
            background: "var(--sodium-500)",
            animation: "milestone-halo 1.4s ease-out infinite",
            pointerEvents: "none",
          }}
        />
      )}
      <svg width={w} height={h} viewBox="0 0 40 52" style={{ position: "relative" }}>
        <BandPatternDefs />
        {/* body: 12-42 */}
        <rect
          x={1}
          y={12}
          width={38}
          height={30}
          fill={selected ? "var(--bitumen-200)" : "var(--surface)"}
          stroke="var(--bitumen-400)"
          strokeWidth={1}
        />
        {/* cap: 0-12, rounded top corners per §7.1 */}
        <path d="M11 0 H29 A10 10 0 0 1 39 10 V12 H1 V10 A10 10 0 0 1 11 0 Z" fill={fill} />
        {fill === "none" && (
          <path
            d="M11 0 H29 A10 10 0 0 1 39 10 V12 H1 V10 A10 10 0 0 1 11 0 Z"
            fill="none"
            stroke="var(--risk-none)"
            strokeWidth={1.5}
            strokeDasharray="3 2"
          />
        )}
        {selected && (
          <path
            d="M11 0 H29 A10 10 0 0 1 39 10 V12 H1 V10 A10 10 0 0 1 11 0 Z"
            fill="none"
            stroke="var(--sodium-500)"
            strokeWidth={2}
          />
        )}
        {/* letter token */}
        <text
          x={20}
          y={9}
          textAnchor="middle"
          fontFamily="var(--font-telemetry)"
          fontSize={12}
          fill="var(--ink-inverse)"
        >
          {band.letter}
        </text>
        {/* sub-label */}
        <text
          x={20}
          y={31}
          textAnchor="middle"
          fontFamily="var(--font-telemetry)"
          fontSize={11}
          fill="var(--ink-primary)"
        >
          {subLabel}
        </text>
        {/* pointer stem (42-46) + 6px triangle foot (46-52) */}
        <line x1={20} y1={42} x2={20} y2={46} stroke="var(--bitumen-400)" strokeWidth={2} />
        <path d="M16 46 H24 L20 52 Z" fill="var(--bitumen-400)" />
      </svg>
    </span>
  );
}
