export type MapLayer = "risk" | "weather" | "traffic" | "blackspots";

const LAYERS: { id: MapLayer; label: string; available: boolean }[] = [
  { id: "risk", label: "Risk", available: true },
  { id: "weather", label: "Weather", available: false },
  { id: "traffic", label: "Traffic", available: false },
  { id: "blackspots", label: "Blackspots (iRAD)", available: false },
];

export interface LayerControlProps {
  active: MapLayer;
  onChange: (layer: MapLayer) => void;
}

/** Bottom-left analytical-comparison card (UX-APPFLOW.md §21.1). Only
 * `Risk` is wired to real data. Weather/Traffic/Blackspots stay visible
 * but disabled rather than hidden or faked -- there's no ingested iRAD
 * blackspot dataset or weather/traffic tile source in this MVP, and the
 * project's honesty principle (§2 P2) says an unavailable feed is shown
 * as unavailable, never silently omitted or invented. */
export function LayerControl({ active, onChange }: LayerControlProps) {
  return (
    <div
      style={{
        position: "absolute",
        left: 12,
        bottom: 12,
        zIndex: 500,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: 10,
        fontFamily: "var(--font-ui)",
        fontSize: 13,
        color: "var(--ink-primary)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
      }}
    >
      {LAYERS.map((layer) => (
        <label
          key={layer.id}
          title={layer.available ? undefined : `${layer.label} — not available in this MVP`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "3px 0",
            opacity: layer.available ? 1 : 0.45,
            cursor: layer.available ? "pointer" : "not-allowed",
          }}
        >
          <input
            type="radio"
            name="map-layer"
            checked={active === layer.id}
            disabled={!layer.available}
            onChange={() => layer.available && onChange(layer.id)}
          />
          {layer.label}
        </label>
      ))}
    </div>
  );
}
