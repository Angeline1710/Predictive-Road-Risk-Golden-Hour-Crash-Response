import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MapContainer, Marker, TileLayer } from "react-leaflet";
import { api, recentLatencyP95 } from "../lib/api";
import type { AlertResponse } from "../lib/api";
import { Shell } from "../components/Shell";
import { GoldenHourDial } from "../components/GoldenHourDial";
import { ChannelBadge } from "../components/ChannelBadge";
import { SimulationSeal } from "../components/SimulationSeal";
import { SEVERITY_BANDS, severityKeyFromApi } from "../lib/bands";
import type { HonestyFeed } from "../components/SystemHonestyBar";

// Same hardcoded honesty-feed status every other page shows -- the backend
// has no /health/feeds endpoint yet (LiveOperations.tsx's own note applies
// here unchanged).
const HONESTY_FEEDS: HonestyFeed[] = [
  { name: "weather", status: "down", ageLabel: "no API key configured" },
  { name: "sms gw", status: "healthy", ageLabel: "" },
];

const NA = "Not available";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          fontFamily: "var(--font-ui)",
          fontWeight: 600,
          fontSize: 11,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--ink-muted)",
          marginBottom: 8,
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
      <span style={{ fontFamily: "var(--font-ui)", fontSize: 13, color: "var(--ink-secondary)" }}>{label}</span>
      <span
        style={{
          fontFamily: "var(--font-telemetry)",
          fontSize: 13,
          color: valueColor ?? "var(--ink-primary)",
          textAlign: "right",
        }}
      >
        {value}
      </span>
    </div>
  );
}

/** UX-APPFLOW.md §22. Opened from a Live Operations card via
 * `IncidentCard`'s "Details →" affordance. */
export function IncidentDetail() {
  const { uuid } = useParams<{ uuid: string }>();
  const navigate = useNavigate();
  const [, forceTick] = useState(0);

  // Golden Hour Dial and "N min ago" both need to keep ticking without a
  // refetch -- same pattern LiveOperations.tsx already uses.
  useEffect(() => {
    const id = setInterval(() => forceTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const query = useQuery({
    queryKey: ["alerts", "detail", uuid],
    queryFn: () => api.getAlert(uuid!),
    enabled: !!uuid,
  });

  return (
    <Shell
      title="Incident Detail"
      active="incidents"
      honestyFeeds={HONESTY_FEEDS}
      latencyMs={recentLatencyP95() ?? undefined}
      latencyLabel="API p95 (client)"
    >
      <div style={{ height: "100%", overflowY: "auto" }}>
        <div
          data-print-hide
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 20px",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <button
            onClick={() => navigate(-1)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--ink-secondary)",
              fontFamily: "var(--font-ui)",
              fontSize: 13,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            ← Incidents
          </button>
          {query.data && <ExportMenu alert={query.data} />}
        </div>

        {query.isLoading && (
          <p style={{ padding: 20, color: "var(--ink-muted)", fontSize: 13 }}>Loading…</p>
        )}
        {query.isError && (
          <p style={{ padding: 20, color: "var(--flare-500)", fontSize: 13 }}>
            Could not reach the API — {(query.error as Error).message}
          </p>
        )}
        {query.data && <DetailBody alert={query.data} />}
      </div>
    </Shell>
  );
}

function ExportMenu({ alert }: { alert: AlertResponse }) {
  const [open, setOpen] = useState(false);

  function downloadGeoJson() {
    // A real GeoJSON Feature built from the response's own fields -- no
    // separate export-formatting service, so there's nothing here that
    // could diverge from what the page itself shows.
    const feature = {
      type: "Feature",
      geometry: alert.lat != null && alert.lon != null
        ? { type: "Point", coordinates: [alert.lon, alert.lat] }
        : null,
      properties: {
        alert_uuid: alert.alert_uuid,
        severity: alert.severity,
        status: alert.status,
        occurred_at: alert.occurred_at,
        landmark: alert.landmark,
        is_simulated: alert.is_simulated,
        risk_band: alert.risk_context?.band ?? null,
        risk_score: alert.risk_context?.score ?? null,
        dispatch_ticket_id: alert.dispatch?.ticket_id ?? null,
      },
    };
    const blob = new Blob([JSON.stringify(feature, null, 2)], { type: "application/geo+json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `incident-${alert.alert_uuid}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          background: "var(--bitumen-200)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)",
          color: "var(--ink-primary)",
          fontFamily: "var(--font-ui)",
          fontSize: 12,
          padding: "6px 12px",
          cursor: "pointer",
        }}
      >
        Export ▾
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            right: 0,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
            zIndex: 10,
            minWidth: 180,
          }}
        >
          {/* Print/Save-as-PDF is the browser's own print pipeline against
              this page's live DOM (index.css's @media print rules), so the
              Simulation Seal renders in the PDF at full fidelity per
              §22 -- there's no separate PDF template to keep in sync. */}
          <MenuItem onClick={() => { setOpen(false); window.print(); }}>Print / Save as PDF</MenuItem>
          <MenuItem onClick={() => { setOpen(false); downloadGeoJson(); }}>Download GeoJSON</MenuItem>
        </div>
      )}
    </div>
  );
}

function MenuItem({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        background: "transparent",
        border: "none",
        color: "var(--ink-primary)",
        fontFamily: "var(--font-ui)",
        fontSize: 13,
        padding: "8px 12px",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bitumen-200)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {children}
    </button>
  );
}

function DetailBody({ alert }: { alert: AlertResponse }) {
  const severity = alert.severity ? SEVERITY_BANDS[severityKeyFromApi(alert.severity)] : SEVERITY_BANDS.minor;
  const occurredAt = alert.occurred_at ? new Date(alert.occurred_at) : null;
  const elapsedSeconds = occurredAt ? (Date.now() - occurredAt.getTime()) / 1000 : 0;
  const agoMinutes = Math.round(elapsedSeconds / 60);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 320px", gap: 24, padding: 20 }}>
      {/* Left -- identity */}
      <div>
        <GoldenHourDial elapsedSeconds={elapsedSeconds} size="detail" />

        <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "var(--font-ui)", fontWeight: 700, fontSize: 20, color: severity.cssVar }}>
            {alert.severity ?? "UNKNOWN"}
          </span>
          {alert.channel && <ChannelBadge channel={alert.channel} hasTrace={alert.has_trace} />}
        </div>

        {occurredAt && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontFamily: "var(--font-telemetry)", fontSize: 14, color: "var(--ink-primary)" }}>
              {occurredAt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })} IST
            </div>
            <div style={{ fontFamily: "var(--font-ui)", fontSize: 12, color: "var(--ink-muted)" }}>
              {agoMinutes <= 0 ? "just now" : `${agoMinutes} min ago`}
            </div>
          </div>
        )}

        {alert.landmark && (
          <div style={{ marginTop: 14, fontFamily: "var(--font-ui)", fontSize: 14, color: "var(--ink-primary)" }}>
            {alert.landmark}
          </div>
        )}

        {alert.lat != null && alert.lon != null && (
          <div style={{ marginTop: 6, fontFamily: "var(--font-telemetry)", fontSize: 12, color: "var(--ink-muted)" }}>
            {alert.lat.toFixed(5)} N<br />
            {alert.lon.toFixed(5)} E<br />
            {alert.gps_accuracy_m != null && `±${Math.round(alert.gps_accuracy_m)} m`}
          </div>
        )}

        {alert.lat != null && alert.lon != null && (
          <div
            data-print-hide
            style={{ marginTop: 12, height: 160, borderRadius: "var(--radius-md)", overflow: "hidden" }}
          >
            <MapContainer
              center={[alert.lat, alert.lon]}
              zoom={14}
              style={{ height: "100%", width: "100%" }}
              zoomControl={false}
              dragging={false}
              scrollWheelZoom={false}
              doubleClickZoom={false}
              attributionControl={false}
            >
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png" />
              <Marker position={[alert.lat, alert.lon]} />
            </MapContainer>
          </div>
        )}
      </div>

      {/* Centre -- evidence */}
      <div>
        <Panel title="Sensor evidence">
          {/* No real {t,g}[] samples exist to hand TraceSparkline in either
              case -- there is no GET endpoint to retrieve sensor_traces
              bytes yet, even for alerts with has_trace=true (only a
              planned POST upload route exists per PRD.md). Rendering the
              chart itself with an empty dataset would look like a broken
              graph rather than an honest gap, so both states are a plain
              message instead, worded to the two real underlying reasons. */}
          <div style={{ color: "var(--ink-muted)", fontSize: 13, fontFamily: "var(--font-ui)" }}>
            {alert.has_trace
              ? "A sensor trace was recorded for this alert, but there is no server-side endpoint yet to retrieve the raw samples (only a planned upload route exists) -- see android/README.md and backend/README.md for the real state of this gap."
              : "No sensor trace was recorded for this alert."}
          </div>
        </Panel>

        <Panel title="Conditions at impact">
          <Row label="Weather" value={alert.conditions?.weather ?? NA} />
          <Row
            label="Visibility"
            value={alert.conditions?.visibility_m != null ? `${Math.round(alert.conditions.visibility_m)} m` : NA}
          />
          <Row label="Light" value={alert.conditions?.light ?? NA} />
          <Row label="Traffic" value={alert.conditions?.traffic_density ?? NA} />
          <Row
            label="Segment risk"
            value={
              alert.risk_context
                ? `${alert.risk_context.score.toFixed(2)} ${alert.risk_context.band[0]}`
                : "No matched segment"
            }
          />
        </Panel>

        <Panel title="Top risk factors">
          {alert.risk_context && alert.risk_context.top_factors.length > 0 ? (
            alert.risk_context.top_factors.map((f) => (
              <div key={f} style={{ fontFamily: "var(--font-telemetry)", fontSize: 13, color: "var(--ink-primary)", padding: "3px 0" }}>
                {f}
              </div>
            ))
          ) : (
            <div style={{ fontFamily: "var(--font-ui)", fontSize: 13, color: "var(--ink-muted)" }}>{NA}</div>
          )}
        </Panel>

        <Panel title="Impact mechanics">
          <Row label="Peak" value={alert.motion?.peak_g != null ? `${alert.motion.peak_g.toFixed(1)} g` : NA} />
          <Row
            label="Delta-V"
            value={alert.motion?.delta_v_kmh != null ? `${alert.motion.delta_v_kmh.toFixed(1)} km/h` : NA}
          />
          <Row label="Direction" value={alert.motion?.impact_direction ?? NA} />
          <Row label="Rollover" value={alert.motion ? (alert.motion.rollover ? "Yes" : "No") : NA} />
          <Row
            label="Still moving"
            value={alert.motion?.still_moving == null ? "Unknown" : alert.motion.still_moving ? "Yes" : "No"}
          />
        </Panel>
      </div>

      {/* Right -- action and disclosure */}
      <div>
        <SimulationSeal
          ticketId={alert.dispatch?.ticket_id ?? null}
          assignmentLine={alert.landmark ?? undefined}
        />

        <div style={{ marginTop: 20 }}>
          <Panel title="Victim details">
            <Row label="Occupants" value={alert.occupant_hint != null ? String(alert.occupant_hint) : "Not recorded"} />
            <Row label="Blood group" value={NA} />
            <Row label="Conditions" value={NA} />
            <Row label="Language" value={NA} />
          </Panel>
          <div style={{ fontFamily: "var(--font-ui)", fontSize: 11, color: "var(--ink-muted)", marginTop: -8, marginBottom: 20 }}>
            Medical details aren't collected by this deployment yet -- see android/README.md's
            onboarding scope notes.
          </div>
        </div>

        <Panel title="Timeline">
          {alert.timeline.length === 0 ? (
            <div style={{ fontFamily: "var(--font-ui)", fontSize: 13, color: "var(--ink-muted)" }}>{NA}</div>
          ) : (
            alert.timeline.map((e, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
                <span style={{ fontFamily: "var(--font-ui)", fontSize: 13, color: "var(--highway-300)" }}>
                  ● {e.status}
                </span>
                <span style={{ fontFamily: "var(--font-telemetry)", fontSize: 12, color: "var(--ink-muted)" }}>
                  {new Date(e.at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>
            ))
          )}
        </Panel>
      </div>
    </div>
  );
}
