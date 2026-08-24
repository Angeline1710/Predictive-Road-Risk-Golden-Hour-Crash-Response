import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useThemeStore } from "../lib/theme";
import type { HonestyFeed } from "./SystemHonestyBar";
import { SystemHonestyBar } from "./SystemHonestyBar";

export type NavDestination = "operations" | "incidents" | "risk-map" | "analytics" | "simulator";

// UX-APPFLOW.md §25: "In production builds the nav item is absent, not
// disabled" for the Simulator Console -- mirrors the backend's own
// RRX_DEMO_MODE gate (app/main.py only registers /sim/* at all when
// settings.demo_mode is true, config.py defaults it true). Unset ->
// visible, matching that same default; a real production build sets
// VITE_DEMO_MODE=false explicitly to make it disappear.
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== "false";

// "Incidents" stays disabled here on purpose even though /incidents/:uuid
// is now a real route (IncidentDetail.tsx) -- that route only has a
// meaning once a specific alert_uuid is known, reached by opening a card
// from Live Operations' rail, not by a standalone "Incidents" nav
// destination this pass doesn't build. Flipping this to built:true would
// need somewhere real for the click to land.
const NAV_ITEMS: { id: NavDestination; label: string; glyph: string; built: boolean; path: string }[] = [
  { id: "operations", label: "Live Operations", glyph: "▣", built: true, path: "/" },
  { id: "incidents", label: "Incidents", glyph: "◈", built: false, path: "" },
  { id: "risk-map", label: "Risk Map", glyph: "◐", built: true, path: "/risk-map" },
  { id: "analytics", label: "Analytics", glyph: "▤", built: true, path: "/analytics" },
  ...(DEMO_MODE ? [{ id: "simulator" as const, label: "Simulator", glyph: "⚗", built: true, path: "/simulator" }] : []),
];

export interface ShellProps {
  title: string;
  active: NavDestination;
  role?: "OPERATOR" | "ANALYST" | "ADMIN";
  honestyFeeds: HonestyFeed[];
  latencyMs?: number;
  latencyLabel?: string;
  deviceCount?: number;
  children: ReactNode;
}

/** App shell -- nav rail, top bar, honesty bar (UX-APPFLOW.md §20). Live
 * Operations, Risk Map, Simulator Console, and Analytics are all built now
 * -- every dashboard nav item is either real or (Incidents) intentionally
 * absent as a standalone destination (see the NAV_ITEMS comment above). */
export function Shell({ title, active, role = "OPERATOR", honestyFeeds, latencyMs, latencyLabel, deviceCount, children }: ShellProps) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--ground)" }}>
      <nav
        data-print-hide
        style={{
          width: 64,
          flexShrink: 0,
          background: "var(--highway-700)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: 16,
          gap: 4,
        }}
      >
        {NAV_ITEMS.map((item) => (
          <NavButton key={item.id} item={item} isActive={item.id === active} />
        ))}
      </nav>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          data-print-hide
          style={{
            height: 56,
            flexShrink: 0,
            background: "var(--bitumen-100)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 20px",
          }}
        >
          <h1
            style={{
              fontFamily: "var(--font-ui)",
              fontWeight: 600,
              fontSize: 22,
              lineHeight: 1.3,
              color: "var(--ink-primary)",
              margin: 0,
            }}
          >
            {title}
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label="Toggle theme"
              style={{
                background: "var(--bitumen-200)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--ink-secondary)",
                fontFamily: "var(--font-ui)",
                fontSize: 12,
                padding: "6px 10px",
                cursor: "pointer",
              }}
            >
              {theme === "dark" ? "Dark" : "Light"}
            </button>
            <span
              style={{
                fontFamily: "var(--font-ui)",
                fontWeight: 500,
                fontSize: 11,
                letterSpacing: "0.06em",
                color: "var(--sodium-500)",
                border: "1px solid var(--sodium-500)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
              }}
            >
              {role}
            </span>
          </div>
        </header>

        <main style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>{children}</main>

        <div data-print-hide>
          <SystemHonestyBar feeds={honestyFeeds} latencyMs={latencyMs} latencyLabel={latencyLabel} deviceCount={deviceCount} />
        </div>
      </div>
    </div>
  );
}

function NavButton({ item, isActive }: { item: (typeof NAV_ITEMS)[number]; isActive: boolean }) {
  const navigate = useNavigate();
  return (
    <button
      title={item.built ? item.label : `${item.label} — not built yet`}
      disabled={!item.built}
      onClick={item.built ? () => navigate(item.path) : undefined}
      style={{
        width: 64,
        height: 48,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 20,
        background: isActive ? "var(--bitumen-300)" : "transparent",
        border: "none",
        borderLeft: isActive ? "3px solid var(--sodium-500)" : "3px solid transparent",
        color: isActive ? "var(--sodium-500)" : item.built ? "var(--paper-200)" : "var(--bitumen-500)",
        cursor: item.built ? "pointer" : "not-allowed",
      }}
    >
      {item.glyph}
    </button>
  );
}
