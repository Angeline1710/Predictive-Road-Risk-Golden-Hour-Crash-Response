import { useState } from "react";
import type { HeatCell } from "../lib/api";
import { RISK_BANDS, bandKeyFromApi } from "../lib/bands";
import { BandPatternDefs, bandFill } from "./BandPatternDefs";

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]; // dow 0=Monday, matches Python's datetime.weekday()

export interface RiskHeatGridProps {
  cells: HeatCell[];
  className?: string;
}

/** UX-APPFLOW.md §23's Corridor mode: "a 24h x 7d heat-grid ... every
 * cell inspectable." Real risk_model_v1 output for one representative
 * segment (GET /risk/heatgrid), not synthesized client-side -- every one
 * of the 168 cells is a real model prediction, batched into a single
 * backend call (see app/ml/risk_model.py's predict_heatgrid docstring). */
export function RiskHeatGrid({ cells, className }: RiskHeatGridProps) {
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  const cellSize = 20;
  const gap = 1;
  const labelW = 32;

  const byKey = new Map(cells.map((c) => [`${c.dow}-${c.hour}`, c]));
  const hovered = hoverKey ? byKey.get(hoverKey) : null;

  return (
    <div className={className} style={{ position: "relative" }}>
      <div style={{ display: "flex", marginLeft: labelW, marginBottom: 2 }}>
        {Array.from({ length: 24 }, (_, h) => (
          <div
            key={h}
            style={{
              width: cellSize, flexShrink: 0, textAlign: "center",
              fontFamily: "var(--font-telemetry)", fontSize: 9, color: "var(--ink-muted)",
            }}
          >
            {h % 4 === 0 ? h : ""}
          </div>
        ))}
      </div>

      <svg width={labelW + 24 * (cellSize + gap)} height={7 * (cellSize + gap)} style={{ display: "block" }}>
        <BandPatternDefs />
        {DOW_LABELS.map((label, dow) => (
          <text
            key={label}
            x={labelW - 6}
            y={dow * (cellSize + gap) + cellSize / 2 + 4}
            textAnchor="end"
            fontFamily="var(--font-ui)"
            fontSize={11}
            fill="var(--ink-secondary)"
          >
            {label}
          </text>
        ))}
        {cells.map((c) => {
          const key = `${c.dow}-${c.hour}`;
          const spec = RISK_BANDS[bandKeyFromApi(c.band)];
          return (
            <rect
              key={key}
              x={labelW + c.hour * (cellSize + gap)}
              y={c.dow * (cellSize + gap)}
              width={cellSize}
              height={cellSize}
              fill={bandFill(spec)}
              stroke={hoverKey === key ? "var(--sodium-500)" : "var(--bitumen-400)"}
              strokeWidth={hoverKey === key ? 2 : 0.5}
              onMouseEnter={() => setHoverKey(key)}
              onMouseLeave={() => setHoverKey((cur) => (cur === key ? null : cur))}
              style={{ cursor: "default" }}
            />
          );
        })}
      </svg>

      {hovered && (
        <div
          role="tooltip"
          style={{
            position: "absolute",
            top: hovered.dow * (cellSize + gap),
            left: labelW + hovered.hour * (cellSize + gap) + cellSize + 6,
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
            pointerEvents: "none",
          }}
        >
          <div>{DOW_LABELS[hovered.dow]} {String(hovered.hour).padStart(2, "0")}:00</div>
          <div>{hovered.band} · {hovered.score.toFixed(3)}</div>
          {hovered.top_factor && <div style={{ color: "var(--ink-muted)" }}>{hovered.top_factor}</div>}
        </div>
      )}
    </div>
  );
}
