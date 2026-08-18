import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, connectEvents, recentLatencyP95 } from "../lib/api";
import type { AlertCreatedData, AlertStatusChangedData, AlertSummary } from "../lib/api";
import { Shell } from "../components/Shell";
import { LiveMap, CORRIDOR_BOUNDS } from "../components/LiveMap";
import { LayerControl, type MapLayer } from "../components/LayerControl";
import { TimeScrubber } from "../components/TimeScrubber";
import { IncidentCard, isUnacknowledged } from "../components/IncidentCard";
import { useThemeStore } from "../lib/theme";
import type { HonestyFeed } from "../components/SystemHonestyBar";

const GOLDEN_HOUR_S = 3600;

function remainingSeconds(occurredAt: string): number {
  return GOLDEN_HOUR_S - (Date.now() - new Date(occurredAt).getTime()) / 1000;
}

/** Unacknowledged first, then by Golden Hour remaining ascending -- never
 * by recency (UX-APPFLOW.md §21.2: "the incident with 8 minutes left
 * matters more than the one from 30 seconds ago"). */
function sortIncidents(list: AlertSummary[]): AlertSummary[] {
  return [...list].sort((a, b) => {
    const aUnack = isUnacknowledged(a.status);
    const bUnack = isUnacknowledged(b.status);
    if (aUnack !== bUnack) return aUnack ? -1 : 1;
    return remainingSeconds(a.occurred_at) - remainingSeconds(b.occurred_at);
  });
}

export function LiveOperations() {
  const setTheme = useThemeStore((s) => s.setTheme);
  const queryClient = useQueryClient();

  const [liveIncidents, setLiveIncidents] = useState<AlertSummary[]>([]);
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);
  const [activeLayer, setActiveLayer] = useState<MapLayer>("risk");
  const [minutesAgo, setMinutesAgo] = useState(0);
  const [zoom, setZoom] = useState(13);
  const [, forceTick] = useState(0);

  useEffect(() => {
    setTheme("dark"); // Live Operations defaults dark -- UX-APPFLOW.md §20
  }, [setTheme]);

  // Re-render every second so Golden Hour Dials and the incident sort order
  // (which depends on elapsed time) stay live without a data refetch.
  useEffect(() => {
    const id = setInterval(() => forceTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const atTime = useMemo(() => new Date(Date.now() - minutesAgo * 60_000), [minutesAgo]);

  const initialAlertsQuery = useQuery({
    queryKey: ["alerts", "list"],
    queryFn: () => api.listAlerts(24, 200),
    refetchInterval: 60_000,
  });

  const riskQuery = useQuery({
    queryKey: ["risk", "bbox", atTime.toISOString().slice(0, 13)], // bucket by hour -- matches Model B's segment×hour grain
    queryFn: () =>
      api.riskBbox(CORRIDOR_BOUNDS[0][0], CORRIDOR_BOUNDS[0][1], CORRIDOR_BOUNDS[1][0], CORRIDOR_BOUNDS[1][1], 1000),
  });

  // Seed the live-updating incident list from the cold-start snapshot.
  useEffect(() => {
    if (initialAlertsQuery.data) setLiveIncidents(initialAlertsQuery.data);
  }, [initialAlertsQuery.data]);

  useEffect(() => {
    return connectEvents((event) => {
      if (event.type === "alert.created") {
        const d = event.data as unknown as AlertCreatedData;
        setLiveIncidents((prev) => {
          if (prev.some((a) => a.alert_uuid === d.alert_uuid)) return prev;
          const summary: AlertSummary = {
            alert_uuid: d.alert_uuid,
            status: "RECEIVED",
            severity: d.severity,
            channel: d.channel,
            occurred_at: event.at,
            received_at: event.at,
            lat: d.lat,
            lon: d.lon,
            segment_id: null,
            landmark: null,
            risk_score: null,
            risk_band: null,
            is_simulated: false,
            has_trace: false,
            ticket_id: null,
          };
          return [summary, ...prev];
        });
      } else if (event.type === "alert.status_changed") {
        const d = event.data as unknown as AlertStatusChangedData;
        setLiveIncidents((prev) =>
          prev.map((a) => (a.alert_uuid === d.alert_uuid ? { ...a, status: d.status, ticket_id: d.ticket_id ?? a.ticket_id } : a))
        );
      }
      // A status change can also move a segment's near-term risk; cheapest
      // correct thing to do is let the next natural risk refetch pick it up
      // rather than hand-patching scores from a partial event payload.
      queryClient.invalidateQueries({ queryKey: ["risk", "bbox"], exact: false, refetchType: "none" });
    });
  }, [queryClient]);

  // `atTime` is only a meaningful upper bound while scrubbed -- it's
  // computed once per `minutesAgo` change, not every tick, so applying it
  // in live mode (minutesAgo === 0) would freeze the cutoff at whatever
  // moment the page happened to mount and silently hide every incident
  // reported after that, which is the opposite of what "live" means here.
  const visibleIncidents = useMemo(
    () =>
      sortIncidents(
        minutesAgo === 0
          ? liveIncidents
          : liveIncidents.filter((a) => new Date(a.occurred_at).getTime() <= atTime.getTime())
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- also depends on the 1s tick for sort order
    [liveIncidents, atTime, minutesAgo]
  );

  const unacknowledgedCount = visibleIncidents.filter((a) => isUnacknowledged(a.status)).length;

  const deviceCountQuery = useQuery({
    queryKey: ["devices", "count"],
    queryFn: api.deviceCount,
    refetchInterval: 60_000,
  });

  // Hardcoded, not queried -- the backend has no feed-status endpoint yet.
  // True for this deployment (backend/app/config.py's openweather_api_key
  // defaults unset), but would go stale the moment someone configures a
  // real key. A real /v1/health/feeds endpoint is the correct fix; tracked
  // as a gap rather than built here, same posture as risk/route etc.
  const honestyFeeds: HonestyFeed[] = [
    { name: "weather", status: "down", ageLabel: "no API key configured" },
    { name: "sms gw", status: "healthy", ageLabel: "" },
  ];

  return (
    <Shell
      title="Live Operations"
      active="operations"
      honestyFeeds={honestyFeeds}
      latencyMs={recentLatencyP95() ?? undefined}
      latencyLabel="API p95 (client)"
      deviceCount={deviceCountQuery.data?.active}
    >
      <div style={{ display: "flex", height: "100%" }}>
        <div style={{ flex: 1, position: "relative" }}>
          {minutesAgo > 0 && (
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                zIndex: 600,
                textAlign: "center",
                background: "var(--sodium-500)",
                color: "var(--ink-inverse)",
                fontFamily: "var(--font-ui)",
                fontWeight: 600,
                fontSize: 12,
                letterSpacing: "0.04em",
                padding: "4px 0",
              }}
            >
              HISTORICAL — {atTime.toLocaleString("en-IN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" })}
            </div>
          )}

          <LiveMap
            riskSegments={riskQuery.data ?? []}
            showRisk={activeLayer === "risk"}
            incidents={visibleIncidents}
            selectedUuid={selectedUuid}
            onSelectIncident={setSelectedUuid}
            zoom={zoom}
            onZoomChange={setZoom}
          />

          <LayerControl active={activeLayer} onChange={setActiveLayer} />
          <TimeScrubber
            minutesAgo={minutesAgo}
            onChange={setMinutesAgo}
            scrubbedLabel={minutesAgo < 60 ? `${minutesAgo}m` : `${(minutesAgo / 60).toFixed(1)}h`}
          />
        </div>

        <aside
          style={{
            width: 400,
            flexShrink: 0,
            borderLeft: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            background: "var(--ground)",
          }}
        >
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-ui)",
                fontWeight: 600,
                fontSize: 11,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--ink-muted)",
              }}
            >
              Live incidents
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontFamily: "var(--font-telemetry)", fontSize: 18, color: "var(--ink-primary)" }}>
                {visibleIncidents.length}
              </span>
              {unacknowledgedCount > 0 && (
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--flare-500)" }} aria-hidden />
              )}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
            {initialAlertsQuery.isLoading && (
              <p style={{ color: "var(--ink-muted)", fontSize: 13 }}>Loading…</p>
            )}
            {initialAlertsQuery.isError && (
              <p style={{ color: "var(--flare-500)", fontSize: 13 }}>
                Could not reach the API — {(initialAlertsQuery.error as Error).message}
              </p>
            )}
            {!initialAlertsQuery.isLoading && visibleIncidents.length === 0 && (
              <p style={{ color: "var(--ink-muted)", fontSize: 13 }}>No incidents in the last 24 hours.</p>
            )}
            {visibleIncidents.map((alert) => (
              <IncidentCard
                key={alert.alert_uuid}
                alert={alert}
                selected={alert.alert_uuid === selectedUuid}
                onSelect={() => setSelectedUuid(alert.alert_uuid)}
              />
            ))}
          </div>
        </aside>
      </div>
    </Shell>
  );
}
