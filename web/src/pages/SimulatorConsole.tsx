import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, recentLatencyP95 } from "../lib/api";
import type { GatewayMode, Severity } from "../lib/api";
import { Shell } from "../components/Shell";
import type { HonestyFeed } from "../components/SystemHonestyBar";

const HONESTY_FEEDS: HonestyFeed[] = [
  { name: "weather", status: "down", ageLabel: "no API key configured" },
  { name: "sms gw", status: "healthy", ageLabel: "" },
];

// backend/app/api/sim.py's own default -- NH-45 near Guduvancheri toll,
// Chengalpattu (PRD §10.1's worked example, the frozen demo corridor).
const DEMO_LAT = 12.91845;
const DEMO_LON = 80.22456;

const SEVERITIES: Severity[] = ["MINOR", "MODERATE", "SEVERE", "CRITICAL"];
const GATEWAY_MODES: { value: GatewayMode; label: string; note: string }[] = [
  { value: "ok", label: "OK", note: "responds normally" },
  { value: "slow", label: "Slow", note: "artificial delay before responding" },
  { value: "timeout", label: "Timeout", note: "never responds -- exercises the never-reject fallback queue" },
  { value: "reject", label: "Reject", note: "declines the incident outright" },
];

interface LogEntry {
  at: string;
  text: string;
  alertUuid?: string;
}

/** UX-APPFLOW.md §25. Demo-only, gated by an environment flag per spec --
 * Shell.tsx's NAV_ITEMS only includes this destination when VITE_DEMO_MODE
 * isn't explicitly "false", mirroring the backend's own RRX_DEMO_MODE gate
 * (app/main.py only registers /sim/* at all when settings.demo_mode is
 * true). The spec's OTHER gate, role, is NOT enforced here -- there is no
 * real operator/analyst login anywhere in this dashboard yet (see
 * backend/README.md's "dashboard-facing RBAC: Not implemented" row), so
 * pretending a role check exists client-side would be exactly the kind of
 * fake gate this project's honesty principle exists to prevent.
 *
 * Inject crash and Gateway mode are real -- both POST straight to
 * app/api/sim.py's two endpoints and run through the actual ingest/gateway
 * code paths (UX §25's "Force SMS path" is the same Inject-crash call with
 * channel_hint=SMS, not a separate control, since the backend only exposes
 * one endpoint for both). Feed failure and Scenario playback are NOT
 * built -- neither has a backend endpoint (no injectable weather/traffic
 * feed exists to fail, and there's no scripted-sequence runner), so both
 * render disabled with the real reason in their tooltip. */
export function SimulatorConsole() {
  const navigate = useNavigate();
  const [lat, setLat] = useState(DEMO_LAT);
  const [lon, setLon] = useState(DEMO_LON);
  const [severity, setSeverity] = useState<Severity>("SEVERE");
  const [speedKmh, setSpeedKmh] = useState(68.4);
  const [peakG, setPeakG] = useState(9.1);
  const [channel, setChannel] = useState<"DATA" | "SMS">("DATA");
  const [activeGatewayMode, setActiveGatewayMode] = useState<GatewayMode>("ok");
  const [log, setLog] = useState<LogEntry[]>([]);

  function pushLog(entry: Omit<LogEntry, "at">) {
    setLog((l) => [{ at: new Date().toLocaleTimeString("en-IN", { hour12: false }), ...entry }, ...l].slice(0, 30));
  }

  const injectCrash = useMutation({
    mutationFn: () => api.simCrash({ lat, lon, severity, speed_kmh: speedKmh, peak_g: peakG, channel_hint: channel }),
    onSuccess: (alert) => {
      pushLog({
        text: `Injected ${severity} crash via ${channel} -- status ${alert.status}${alert.dispatch?.ticket_id ? `, ticket ${alert.dispatch.ticket_id}` : ""}`,
        alertUuid: alert.alert_uuid,
      });
    },
    onError: (err) => pushLog({ text: `Inject crash failed -- ${(err as Error).message}` }),
  });

  const setGatewayMode = useMutation({
    mutationFn: (mode: GatewayMode) => api.simGatewayMode(mode),
    onSuccess: (res) => {
      setActiveGatewayMode(res.mode);
      pushLog({ text: `Gateway mode set to ${res.mode}` });
    },
    onError: (err) => pushLog({ text: `Set gateway mode failed -- ${(err as Error).message}` }),
  });

  return (
    <Shell
      title="Simulator Console"
      active="simulator"
      role="ADMIN"
      honestyFeeds={HONESTY_FEEDS}
      latencyMs={recentLatencyP95() ?? undefined}
      latencyLabel="API p95 (client)"
    >
      <div style={{ display: "flex", height: "100%" }}>
        <div style={{ width: 340, flexShrink: 0, background: "var(--surface)", borderRight: "1px solid var(--border)", padding: 16, overflowY: "auto", fontFamily: "var(--font-ui)" }}>
          <SectionLabel>Inject crash</SectionLabel>
          <FieldRow label="Latitude">
            <input type="number" step="0.00001" value={lat} onChange={(e) => setLat(Number(e.target.value))} style={inputStyle} />
          </FieldRow>
          <FieldRow label="Longitude">
            <input type="number" step="0.00001" value={lon} onChange={(e) => setLon(Number(e.target.value))} style={inputStyle} />
          </FieldRow>
          <FieldRow label="Severity">
            <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity)} style={inputStyle}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </FieldRow>
          <FieldRow label="Speed (km/h)">
            <input type="number" step="0.1" value={speedKmh} onChange={(e) => setSpeedKmh(Number(e.target.value))} style={inputStyle} />
          </FieldRow>
          <FieldRow label="Peak g">
            <input type="number" step="0.1" value={peakG} onChange={(e) => setPeakG(Number(e.target.value))} style={inputStyle} />
          </FieldRow>
          <FieldRow label="Channel (Force path)">
            <div style={{ display: "flex", gap: 6 }}>
              {(["DATA", "SMS"] as const).map((c) => (
                <button
                  key={c}
                  onClick={() => setChannel(c)}
                  style={{ ...toggleButtonStyle, ...(channel === c ? toggleButtonActiveStyle : {}) }}
                >
                  {c}
                </button>
              ))}
            </div>
          </FieldRow>
          <button
            onClick={() => injectCrash.mutate()}
            disabled={injectCrash.isPending}
            style={{ ...primaryButtonStyle, marginTop: 4 }}
          >
            {injectCrash.isPending ? "Injecting…" : "Inject crash"}
          </button>
          {channel === "SMS" && (
            <p style={{ fontSize: 11, color: "var(--ink-muted)", marginTop: 6 }}>
              Routes through the real RRX1 encode → parse → ingest path (PRD §16.2 step 5), not a shortcut.
            </p>
          )}

          <SectionLabel style={{ marginTop: 24 }}>Gateway mode</SectionLabel>
          {GATEWAY_MODES.map((m) => (
            <button
              key={m.value}
              onClick={() => setGatewayMode.mutate(m.value)}
              disabled={setGatewayMode.isPending}
              title={m.note}
              style={{
                ...toggleButtonStyle,
                width: "100%",
                justifyContent: "space-between",
                display: "flex",
                marginBottom: 6,
                ...(activeGatewayMode === m.value ? toggleButtonActiveStyle : {}),
              }}
            >
              <span>{m.label}</span>
              {activeGatewayMode === m.value && <span>●</span>}
            </button>
          ))}
          <p style={{ fontSize: 11, color: "var(--ink-muted)", marginTop: 4 }}>
            There's no GET endpoint to read the gateway's current mode, so this reflects the last mode
            <em> this console</em> set -- another client (or a backend restart, which resets to OK) could
            have changed it since.
          </p>

          <SectionLabel style={{ marginTop: 24 }}>Not built</SectionLabel>
          <DisabledRow label="Feed failure" reason="No injectable weather/traffic feed exists to fail -- both are already permanently unavailable in this deployment (no API key configured)." />
          <DisabledRow label="Scenario playback" reason="No scripted-sequence runner exists server- or client-side; each control above fires one action at a time." />
        </div>

        <div style={{ flex: 1, minWidth: 0, overflowY: "auto", padding: 20 }}>
          <SectionLabel>Event log</SectionLabel>
          {log.length === 0 ? (
            <p style={{ color: "var(--ink-muted)", fontSize: 13, fontFamily: "var(--font-ui)" }}>
              Nothing injected yet this session.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {log.map((entry, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
                    padding: "8px 10px", background: "var(--surface)", border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)", fontFamily: "var(--font-telemetry)", fontSize: 12,
                  }}
                >
                  <span style={{ color: "var(--ink-muted)", flexShrink: 0 }}>{entry.at}</span>
                  <span style={{ color: "var(--ink-primary)", flex: 1 }}>{entry.text}</span>
                  {entry.alertUuid && (
                    <button
                      onClick={() => navigate(`/incidents/${entry.alertUuid}`)}
                      style={{ background: "transparent", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", color: "var(--sodium-500)", fontFamily: "var(--font-ui)", fontSize: 11, padding: "3px 8px", cursor: "pointer", flexShrink: 0 }}
                    >
                      View →
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", background: "var(--bitumen-200)", border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)", color: "var(--ink-primary)", fontFamily: "var(--font-telemetry)",
  fontSize: 13, padding: "6px 8px",
};

const toggleButtonStyle: React.CSSProperties = {
  background: "var(--bitumen-200)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
  color: "var(--ink-primary)", fontFamily: "var(--font-ui)", fontSize: 12, padding: "6px 10px",
  cursor: "pointer", flex: 1,
};

const toggleButtonActiveStyle: React.CSSProperties = {
  background: "var(--sodium-500)", color: "var(--bitumen-000)", border: "1px solid var(--sodium-500)", fontWeight: 700,
};

const primaryButtonStyle: React.CSSProperties = {
  width: "100%", background: "var(--sodium-500)", border: "none", borderRadius: "var(--radius-sm)",
  color: "var(--bitumen-000)", fontFamily: "var(--font-ui)", fontWeight: 600, fontSize: 13, padding: "9px 0",
  cursor: "pointer",
};

function SectionLabel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ fontWeight: 600, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-muted)", marginBottom: 10, ...style }}>
      {children}
    </div>
  );
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: "var(--ink-secondary)", marginBottom: 4 }}>{label}</div>
      {children}
    </div>
  );
}

function DisabledRow({ label, reason }: { label: string; reason: string }) {
  return (
    <div title={reason} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 10px", background: "var(--bitumen-200)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", color: "var(--ink-muted)", fontFamily: "var(--font-ui)", fontSize: 12, marginBottom: 6, cursor: "not-allowed" }}>
      <span>{label}</span>
      <span>not built</span>
    </div>
  );
}
