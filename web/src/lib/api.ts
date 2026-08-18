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

// app/schemas/alert.py's AlertResponse
export interface AlertResponse {
  alert_uuid: string;
  status: string;
  segment_id: number | null;
  landmark: string | null;
  risk_context: RiskContext | null;
  dispatch: DispatchInfo | null;
  nearest_units: NearestUnit[];
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

  riskBbox: (minlat: number, minlon: number, maxlat: number, maxlon: number, limit = 500) =>
    request<RiskPoint[]>(
      `/v1/risk/bbox?minlat=${minlat}&minlon=${minlon}&maxlat=${maxlat}&maxlon=${maxlon}&limit=${limit}`
    ),

  simCrash: (body: { lat?: number; lon?: number; severity?: Severity; channel_hint?: "DATA" | "SMS" }) =>
    request<AlertResponse>("/v1/sim/crash", { method: "POST", body: JSON.stringify(body) }),

  simGatewayMode: (mode: "ok" | "slow" | "timeout" | "reject") =>
    request<{ mode: string }>("/v1/sim/gateway/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  deviceCount: () => request<DeviceCount>("/v1/devices/count"),
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
