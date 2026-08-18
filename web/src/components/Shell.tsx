import type { ReactNode } from "react";
import { useThemeStore } from "../lib/theme";
import type { HonestyFeed } from "./SystemHonestyBar";
import { SystemHonestyBar } from "./SystemHonestyBar";

export type NavDestination = "operations" | "incidents" | "risk-map" | "analytics" | "simulator";

const NAV_ITEMS: { id: NavDestination; label: string; glyph: string; built: boolean }[] = [
  { id: "operations", label: "Live Operations", glyph: "▣", built: true },
  { id: "incidents", label: "Incidents", glyph: "◈", built: false },
  { id: "risk-map", label: "Risk Map", glyph: "◐", built: false },
  { id: "analytics", label: "Analytics", glyph: "▤", built: false },
  { id: "simulator", label: "Simulator", glyph: "⚗", built: false },
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

/** App shell -- nav rail, top bar, honesty bar (UX-APPFLOW.md §20). Only
 * Live Operations (task #15) is built; the other four destinations render
 * disabled per the project's honest-degradation posture (§2 P2) rather
 * than linking to pages that don't exist yet. */
export function Shell({ title, active, role = "OPERATOR", honestyFeeds, latencyMs, latencyLabel, deviceCount, children }: ShellProps) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--ground)" }}>
      <nav
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

        <SystemHonestyBar feeds={honestyFeeds} latencyMs={latencyMs} latencyLabel={latencyLabel} deviceCount={deviceCount} />
      </div>
    </div>
  );
}

function NavButton({ item, isActive }: { item: (typeof NAV_ITEMS)[number]; isActive: boolean }) {
  return (
    <button
      title={item.built ? item.label : `${item.label} — not built yet`}
      disabled={!item.built}
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
