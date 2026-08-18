// Risk band / severity constants transcribed from UX-APPFLOW.md §4.7.
// Triple encoding is mandatory (NFR-A3): hue + pattern + letter token, plus
// stroke weight on the map. Never read band identity from colour alone --
// ~8% of Indian men have red-green CVD, and government documents get
// photocopied/faxed in greyscale where hue disappears entirely.

export type RiskBandKey = "low" | "mod" | "high" | "severe" | "none";

export interface BandSpec {
  token: string; // matches tailwind.config.js `risk.*` / `flare-500` etc.
  cssVar: string;
  pattern: "solid" | "hatch45-6" | "hatch45-3" | "crosshatch3" | "dashed";
  letter: string;
  mapStroke: number;
}

export const RISK_BANDS: Record<RiskBandKey, BandSpec> = {
  low: { token: "risk-low", cssVar: "var(--risk-low)", pattern: "solid", letter: "L", mapStroke: 3 },
  mod: { token: "risk-mod", cssVar: "var(--risk-mod)", pattern: "hatch45-6", letter: "M", mapStroke: 4 },
  high: { token: "risk-high", cssVar: "var(--risk-high)", pattern: "hatch45-3", letter: "H", mapStroke: 5 },
  severe: { token: "risk-severe", cssVar: "var(--risk-severe)", pattern: "crosshatch3", letter: "S", mapStroke: 6 },
  none: { token: "risk-none", cssVar: "var(--risk-none)", pattern: "dashed", letter: "–", mapStroke: 2 },
};

// API returns band names capitalized ("Low" | "Moderate" | "High" | "Severe");
// map to the internal lowercase key used for lookups/pattern ids.
export function bandKeyFromApi(band: string): RiskBandKey {
  switch (band.toLowerCase()) {
    case "low":
      return "low";
    case "moderate":
      return "mod";
    case "high":
      return "high";
    case "severe":
      return "severe";
    default:
      return "none";
  }
}

// Incident severities (crash detail, not road risk) reuse the same four hues
// per §7.1 -- "Encodes risk band ... or incident severity ... in its cap."
export type IncidentSeverityKey = "minor" | "moderate" | "severe" | "critical";

export const SEVERITY_BANDS: Record<IncidentSeverityKey, BandSpec> = {
  minor: RISK_BANDS.low,
  moderate: RISK_BANDS.mod,
  severe: RISK_BANDS.high,
  critical: RISK_BANDS.severe,
};

export function severityKeyFromApi(sev: string): IncidentSeverityKey {
  switch (sev.toUpperCase()) {
    case "MINOR":
      return "minor";
    case "MODERATE":
      return "moderate";
    case "SEVERE":
      return "severe";
    case "CRITICAL":
      return "critical";
    default:
      return "minor";
  }
}
