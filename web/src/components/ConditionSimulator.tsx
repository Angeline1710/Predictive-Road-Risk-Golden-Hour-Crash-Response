import type { TrafficOverride, VisibilityOverride, WeatherOverride } from "../lib/api";

export interface SimulatedConditions {
  hour: number | null; // null = real wall-clock time
  weather: WeatherOverride | null;
  visibility: VisibilityOverride | null;
  trafficDensity: TrafficOverride | null;
}

export const LIVE_CONDITIONS: SimulatedConditions = { hour: null, weather: null, visibility: null, trafficDensity: null };

export function isSimulated(c: SimulatedConditions): boolean {
  return c.hour !== null || c.weather !== null || c.visibility !== null || c.trafficDensity !== null;
}

export interface ConditionSimulatorProps {
  value: SimulatedConditions;
  onChange: (value: SimulatedConditions) => void;
}

const WEATHER_OPTIONS: { value: WeatherOverride; label: string }[] = [
  { value: "clear", label: "Clear" },
  { value: "rain", label: "Rain" },
  { value: "fog", label: "Fog" },
];
const VISIBILITY_OPTIONS: { value: VisibilityOverride; label: string }[] = [
  { value: "high", label: "High" },
  { value: "medium", label: "Med" },
  { value: "low", label: "Low" },
];
const TRAFFIC_OPTIONS: { value: TrafficOverride; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Med" },
  { value: "high", label: "High" },
];

/** UX-APPFLOW.md §23's "condition simulator" -- moving these controls
 * re-scores the visible network live via GET /risk/bbox's weather/
 * visibility/traffic_density/at overrides (backend/app/api/risk.py). The
 * spec calls for "sliders" for all four; weather/visibility/traffic are
 * rendered as 3-way segmented controls instead, because risk_model_v1.txt
 * only has three trained categories for each (ml/risk_model/build_panel.py)
 * -- a continuous slider implying finer-grained input than the model can
 * actually use would be dishonest precision, not a UI nicety. Hour-of-day
 * is genuinely continuous (0-23) and is a real slider. */
export function ConditionSimulator({ value, onChange }: ConditionSimulatorProps) {
  const simulated = isSimulated(value);
  const hourDisplay = value.hour ?? new Date().getHours();

  return (
    <div
      style={{
        width: 260,
        flexShrink: 0,
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        padding: 16,
        overflowY: "auto",
        fontFamily: "var(--font-ui)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
          Condition simulator
        </span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.06em",
            padding: "2px 6px",
            borderRadius: "var(--radius-sm)",
            color: simulated ? "var(--sodium-500)" : "var(--ink-muted)",
            border: `1px solid ${simulated ? "var(--sodium-500)" : "var(--border)"}`,
          }}
        >
          {simulated ? "SIMULATED" : "LIVE"}
        </span>
      </div>

      <Field label="Hour of day">
        <input
          type="range"
          min={0}
          max={23}
          value={hourDisplay}
          onChange={(e) => onChange({ ...value, hour: Number(e.target.value) })}
          style={{ width: "100%" }}
        />
        <div style={{ fontFamily: "var(--font-telemetry)", fontSize: 13, color: "var(--ink-primary)", marginTop: 2 }}>
          {String(hourDisplay).padStart(2, "0")}:00 {value.hour === null && "(now)"}
        </div>
      </Field>

      <Field label="Weather">
        <Segmented
          options={WEATHER_OPTIONS}
          selected={value.weather}
          onSelect={(v) => onChange({ ...value, weather: v })}
        />
      </Field>

      <Field label="Visibility">
        <Segmented
          options={VISIBILITY_OPTIONS}
          selected={value.visibility}
          onSelect={(v) => onChange({ ...value, visibility: v })}
        />
      </Field>

      <Field label="Traffic ratio">
        <Segmented
          options={TRAFFIC_OPTIONS}
          selected={value.trafficDensity}
          onSelect={(v) => onChange({ ...value, trafficDensity: v })}
        />
      </Field>

      <button
        onClick={() => onChange(LIVE_CONDITIONS)}
        disabled={!simulated}
        style={{
          width: "100%",
          marginTop: 8,
          background: "var(--bitumen-200)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)",
          color: simulated ? "var(--ink-primary)" : "var(--ink-muted)",
          fontFamily: "var(--font-ui)",
          fontSize: 12,
          padding: "8px 0",
          cursor: simulated ? "pointer" : "not-allowed",
        }}
      >
        Reset to live
      </button>

      <p style={{ marginTop: 16, fontSize: 11, lineHeight: 1.5, color: "var(--ink-muted)" }}>
        Every segment on the map is re-scored by the real model
        (risk_model_v1) under whichever conditions are set above -- this is
        not a client-side approximation.
      </p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 12, color: "var(--ink-secondary)", marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  );
}

function Segmented<T extends string>({
  options,
  selected,
  onSelect,
}: {
  options: { value: T; label: string }[];
  selected: T | null;
  onSelect: (v: T | null) => void;
}) {
  return (
    <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
      {options.map((opt) => {
        const active = selected === opt.value;
        return (
          <button
            key={opt.value}
            onClick={() => onSelect(active ? null : opt.value)}
            style={{
              flex: 1,
              background: active ? "var(--sodium-500)" : "var(--bitumen-200)",
              color: active ? "var(--bitumen-000)" : "var(--ink-primary)",
              border: "none",
              borderRight: "1px solid var(--border)",
              fontFamily: "var(--font-ui)",
              fontSize: 12,
              padding: "6px 0",
              cursor: "pointer",
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
