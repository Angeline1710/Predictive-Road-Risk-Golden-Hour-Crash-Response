// Typed against backend/app/schemas/*.py exactly -- these interfaces are the
// wire contract, not a guess at it. Keep in sync by hand until the backend
// exports an OpenAPI-generated client (PRD's own /openapi.json exists, but
// codegen wasn't wired up in this pass).

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export type Severity = "MINOR" | "MODERATE" | "SEVERE" | "CRITICAL";
export type RiskBand = "Low" | "Moderate" | "High" | "Severe";
export type Channel = "DATA" | "SMS" | "MANUAL_SOS";

export interface RiskContext {
  score: number;
  band: string;
  top_factors: string[];
}

export interface DispatchInfo {
  gateway: string;
  is_simulated: boolean;
  ticket_id: string | null;
  eta_note: string | null;
}

export interface NearestUnit {
  id: number;
  name: string;
  kind: string;
  distance_km: number;
}

// app/schemas/alert.py's MotionOut
export interface Motion {
  speed_kmh: number | null;
  heading_deg: number | null;
  peak_g: number | null;
  delta_v_kmh: number | null;
  impact_direction: string | null;
  rollover: boolean;
  still_moving: boolean | null;
}

// app/schemas/alert.py's ConditionsOut. weather/visibility_m/traffic_density
// are genuinely null in this deployment -- no weather/traffic API key is
// configured server-side (backend/app/services/enrichment.py degrades
// honestly rather than fake a reading). light is always real.
export interface Conditions {
  weather: string | null;
  visibility_m: number | null;
  light: "Day" | "Night";
  traffic_density: string | null;
  conditions_available: boolean;
}

// app/schemas/alert.py's TimelineEventOut -- one row of the real,
// append-only alert_events audit trail.
export interface TimelineEvent {
  status: string;
  at: string;
  actor: string | null;
}

// app/schemas/alert.py's AlertResponse. Everything past alert_uuid/status is
// optional because the same schema also backs POST /alerts's 202 body,
// which PRD §10.4 requires to degrade gracefully rather than error.
export interface AlertResponse {
  alert_uuid: string;
  status: string;
  severity: Severity | null;
  channel: Channel | null;
  occurred_at: string | null;
  received_at: string | null;
  is_simulated: boolean | null;
  lat: number | null;
  lon: number | null;
  gps_accuracy_m: number | null;
  has_trace: boolean;
  segment_id: number | null;
  landmark: string | null;
  risk_context: RiskContext | null;
  dispatch: DispatchInfo | null;
  nearest_units: NearestUnit[];
  motion: Motion | null;
  conditions: Conditions | null;
  // Occupants only -- blood group/medical conditions/language have no real
  // source anywhere in this system yet (see IncidentDetail.tsx's own note).
  occupant_hint: number | null;
  timeline: TimelineEvent[];
}

// app/api/risk.py's risk_bbox condition-simulator overrides -- the exact
// categories risk_model_v1.txt was trained on (ml/risk_model/build_panel.py).
export type WeatherOverride = "clear" | "rain" | "fog";
export type VisibilityOverride = "high" | "medium" | "low";
export type TrafficOverride = "low" | "medium" | "high";

// app/gateways/simulated.py's GatewayMode
export type GatewayMode = "ok" | "slow" | "timeout" | "reject";

// app/api/risk.py's HeatCellOut -- dow 0=Monday..6=Sunday (datetime.weekday()).
export interface HeatCell {
  dow: number;
  hour: number;
  score: number;
  band: RiskBand;
  top_factor: string | null;
}

// app/api/analytics.py's AnalyticsSummary and its nested models
export interface LatencyBucket {
  label: string;
  le_s: number | null;
  count: number;
}
export interface ResponseLatency {
  n: number;
  p50_s: number | null;
  p95_s: number | null;
  p99_s: number | null;
  histogram: LatencyBucket[];
}
export interface ChannelBucket {
  hour: string;
  data: number;
  sms: number;
  manual_sos: number;
}
export interface GoldenHourStats {
  n: number;
  within_60min_pct: number | null;
  within_30min_pct: number | null;
  within_15min_pct: number | null;
}
export interface CoverageStats {
  devices_active: number;
  devices_total: number;
  segment_count: number;
  network_km: number;
  districts: string[];
  responder_unit_count: number;
}
export interface AnalyticsSummary {
  since_hours: number;
  alert_count: number;
  response_latency: ResponseLatency;
  channel_mix: ChannelBucket[];
  golden_hour: GoldenHourStats;
  coverage: CoverageStats;
}

// app/api/risk.py's RiskContextOut
export interface RiskPoint {
  segment_id: number;
  district: string | null;
  road_class: string | null;
  score: number;
  band: RiskBand;
  top_factors: string[];
  model_version: string;
  /** GeoJSON LineString coordinates, [lon, lat] pairs. */
  geometry: [number, number][];
}

// app/schemas/alert.py's AlertSummary -- GET /alerts list row
export interface AlertSummary {
  alert_uuid: string;
  status: string;
  severity: Severity;
  channel: Channel;
  occurred_at: string;
  received_at: string;
  lat: number;
  lon: number;
  segment_id: number | null;
  landmark: string | null;
  risk_score: number | null;
  risk_band: string | null;
  is_simulated: boolean;
  has_trace: boolean;
  ticket_id: string | null;
}

// app/services/events.py's publish_event envelope
export interface RrxEvent {
  type: "alert.created" | "alert.status_changed" | "risk.updated";
  at: string;
  data: Record<string, unknown>;
}

export interface AlertCreatedData {
  alert_uuid: string;
  severity: Severity;
  lat: number;
  lon: number;
  channel: Channel;
}

export interface AlertStatusChangedData {
  alert_uuid: string;
  status: string;
  ticket_id?: string;
  reason?: string;
}

// app/api/devices.py's DeviceCount
export interface DeviceCount {
  active: number;
  active_window_hours: number;
  total: number;
}

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

// Rolling window of observed round-trip times, purely client-side. Exposed
// as "DASHBOARD P95" (not "ingest p95") in the System Honesty Bar -- it's a
// real measurement, but of a different thing than server-side ingest
// latency, and the honesty bar exists precisely to stop that kind of
// conflation (UX-APPFLOW.md §7.7).
const LATENCY_WINDOW = 20;
const recentLatenciesMs: number[] = [];

export function recentLatencyP95(): number | null {
  if (recentLatenciesMs.length === 0) return null;
  const sorted = [...recentLatenciesMs].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.ceil(0.95 * sorted.length) - 1);
  return sorted[idx];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const start = performance.now();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  recentLatenciesMs.push(performance.now() - start);
  if (recentLatenciesMs.length > LATENCY_WINDOW) recentLatenciesMs.shift();
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export const api = {
  getAlert: (uuid: string) => request<AlertResponse>(`/v1/alerts/${uuid}`),

  listAlerts: (sinceHours = 24, limit = 200) =>
    request<AlertSummary[]>(`/v1/alerts?since_hours=${sinceHours}&limit=${limit}`),

  riskPoint: (lat: number, lon: number, at?: string) =>
    request<RiskPoint>(
      `/v1/risk/point?lat=${lat}&lon=${lon}${at ? `&at=${encodeURIComponent(at)}` : ""}`
    ),

  riskBbox: (
    minlat: number, minlon: number, maxlat: number, maxlon: number,
    opts: { limit?: number; at?: string; weather?: WeatherOverride; visibility?: VisibilityOverride; trafficDensity?: TrafficOverride } = {}
  ) => {
    const { limit = 500, at, weather, visibility, trafficDensity } = opts;
    const params = new URLSearchParams({
      minlat: String(minlat), minlon: String(minlon), maxlat: String(maxlat), maxlon: String(maxlon),
      limit: String(limit),
    });
    if (at) params.set("at", at);
    if (weather) params.set("weather", weather);
    if (visibility) params.set("visibility", visibility);
    if (trafficDensity) params.set("traffic_density", trafficDensity);
    return request<RiskPoint[]>(`/v1/risk/bbox?${params}`);
  },

  // app/api/sim.py's SimCrashRequest -- only registered when the backend's
  // RRX_DEMO_MODE is on (defaults true). channel_hint: "SMS" is the real
  // RRX1 encode/parse/ingest round-trip (PRD §16.2 step 5's "airplane mode,
  // alert still lands"), not a separate endpoint -- UX-APPFLOW §25's
  // "Force SMS path" control is this same call with channel_hint set.
  simCrash: (body: {
    lat?: number; lon?: number; severity?: Severity;
    speed_kmh?: number; peak_g?: number; channel_hint?: "DATA" | "SMS";
  }) => request<AlertResponse>("/v1/sim/crash", { method: "POST", body: JSON.stringify(body) }),

  simGatewayMode: (mode: GatewayMode) =>
    request<{ mode: GatewayMode }>("/v1/sim/gateway/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  deviceCount: () => request<DeviceCount>("/v1/devices/count"),

  analyticsSummary: (sinceHours = 24) =>
    request<AnalyticsSummary>(`/v1/analytics/summary?since_hours=${sinceHours}`),

  riskHeatgrid: (segmentId: number) =>
    request<HeatCell[]>(`/v1/risk/heatgrid?segment_id=${segmentId}`),
};

/** PRD §10.3 `WS /ws/events` -- Redis pub/sub fan-out. Auto-reconnects with
 * backoff; the Live Operations view (UX-APPFLOW.md §21) is meant to run on
 * an ops-room display for hours, so a dropped connection must recover on
 * its own, not require a manual page refresh.
 */
export function connectEvents(onEvent: (e: RrxEvent) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retryMs = 1000;

  function connect() {
    if (closed) return;
    ws = new WebSocket(`${WS_BASE}/v1/ws/events`);
    ws.onmessage = (msg) => {
      try {
        onEvent(JSON.parse(msg.data));
      } catch {
        // malformed frame -- drop it, do not crash the live view over one bad message
      }
    };
    ws.onopen = () => {
      retryMs = 1000;
    };
    ws.onclose = () => {
      if (closed) return;
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 30_000);
    };
  }
  connect();

  return () => {
    closed = true;
    ws?.close();
  };
}

export { ApiError };
