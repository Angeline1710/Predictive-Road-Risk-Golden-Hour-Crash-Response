import { useState } from "react";
import type { BandSpec } from "../lib/bands";
import { BandPatternDefs, bandFill } from "./BandPatternDefs";

export interface RibbonSegment {
  segmentId: number | string;
  band: BandSpec;
  score?: number;
  topFactors?: string[];
  distanceKm?: number;
}

export interface SegmentRibbonProps {
  segments: RibbonSegment[];
  /** Index of the "you are here" segment; omit to hide the chevron. */
  currentIndex?: number;
  variant?: "app" | "dashboard";
  onSegmentClick?: (segment: RibbonSegment) => void;
  className?: string;
}

/** Horizontal strip of 500m road segments coloured/hatched by risk band
 * (UX-APPFLOW.md §7.2) -- the product's most-used component. The 500m cell
 * is matched to MoRTH's own iRAD blackspot unit so our output compares
 * cell-for-cell against the official blackspot list. */
export function SegmentRibbon({
  segments,
  currentIndex,
  variant = "app",
  onSegmentClick,
  className,
}: SegmentRibbonProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const cellH = variant === "dashboard" ? 24 : 32;
  const cellW = variant === "dashboard" ? 28 : 36;

  const hovered = hoverIdx !== null ? segments[hoverIdx] : null;

  return (
    <div className={className} style={{ position: "relative" }}>
      {variant === "dashboard" && (
        <div
          style={{
            display: "flex",
            fontFamily: "var(--font-telemetry)",
            fontSize: 10,
            color: "var(--ink-muted)",
            marginBottom: 2,
          }}
        >
          {segments.map((s) => (
            <div key={s.segmentId} style={{ width: cellW, flexShrink: 0, textAlign: "center" }}>
              {s.distanceKm !== undefined ? `${s.distanceKm.toFixed(1)}` : ""}
            </div>
          ))}
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <svg width={segments.length * (cellW + 1)} height={cellH} style={{ display: "block" }}>
          <BandPatternDefs />
          {segments.map((s, i) => (
            <rect
              key={s.segmentId}
              x={i * (cellW + 1)}
              y={0}
              width={cellW}
              height={cellH}
              fill={bandFill(s.band)}
              stroke={hoverIdx === i ? "var(--sodium-500)" : "var(--bitumen-400)"}
              strokeWidth={hoverIdx === i ? 2 : 1}
              onClick={() => onSegmentClick?.(s)}
              onMouseEnter={() => setHoverIdx(i)}
              onMouseLeave={() => setHoverIdx((cur) => (cur === i ? null : cur))}
              style={{ cursor: onSegmentClick ? "pointer" : "default" }}
            />
          ))}
        </svg>
      </div>

      {/* letter row -- greyscale/colour-blind fallback */}
      <div style={{ display: "flex" }}>
        {segments.map((s, i) => (
          <div
            key={s.segmentId}
            style={{
              width: cellW,
              marginLeft: i === 0 ? 0 : 1,
              flexShrink: 0,
              textAlign: "center",
              fontFamily: "var(--font-telemetry)",
              fontSize: 11,
              color: "var(--ink-secondary)",
            }}
          >
            {s.band.letter}
          </div>
        ))}
      </div>

      {/* "you are here" chevron -- fixed position, ribbon scrolls beneath it */}
      {currentIndex !== undefined && currentIndex >= 0 && currentIndex < segments.length && (
        <div
          style={{
            position: "absolute",
            top: cellH + 14,
            left: currentIndex * (cellW + 1) + cellW / 2 - 5,
            width: 0,
            height: 0,
            borderLeft: "5px solid transparent",
            borderRight: "5px solid transparent",
            borderBottom: "7px solid var(--sodium-500)",
          }}
          aria-hidden
        />
      )}

      {hovered && (
        <div
          role="tooltip"
          style={{
            position: "absolute",
            top: -8,
            left: (hoverIdx ?? 0) * (cellW + 1),
            transform: "translateY(-100%)",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "6px 8px",
            fontSize: 11,
            fontFamily: "var(--font-telemetry)",
            color: "var(--ink-primary)",
            whiteSpace: "nowrap",
            boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
            zIndex: 10,
          }}
        >
          <div>SEG {hovered.segmentId}</div>
          {hovered.score !== undefined && <div>score {hovered.score.toFixed(2)}</div>}
          {hovered.topFactors?.slice(0, 3).map((f) => (
            <div key={f} style={{ color: "var(--ink-muted)" }}>
              {f}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
