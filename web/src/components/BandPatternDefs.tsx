import { RISK_BANDS, type BandSpec } from "../lib/bands";

/** Shared <defs> block of SVG patterns for the four risk-band hatch styles
 * (UX-APPFLOW.md §4.7). Keyed by `spec.token` (e.g. "risk-high"), not by
 * the risk-band vs. incident-severity namespace, since Milestone Marker
 * reuses these exact BandSpec objects for both (§7.1: "Encodes risk band
 * ... or incident severity ... in its cap"). Render once per SVG and
 * resolve fills via `bandFill(spec)` so every surface -- map, Segment
 * Ribbon, charts -- draws pixel-identical hatching. */
export function BandPatternDefs() {
  return (
    <defs>
      {Object.values(RISK_BANDS).map((spec) => {
        const id = `band-hatch-${spec.token}`;
        if (spec.pattern === "solid" || spec.pattern === "dashed") {
          return null;
        }
        if (spec.pattern === "hatch45-6") {
          return (
            <pattern key={id} id={id} width={6} height={6} patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
              <rect width={6} height={6} fill={spec.cssVar} fillOpacity={0.28} />
              <line x1={0} y1={0} x2={0} y2={6} stroke={spec.cssVar} strokeWidth={2} />
            </pattern>
          );
        }
        if (spec.pattern === "hatch45-3") {
          return (
            <pattern key={id} id={id} width={3} height={3} patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
              <rect width={3} height={3} fill={spec.cssVar} fillOpacity={0.32} />
              <line x1={0} y1={0} x2={0} y2={3} stroke={spec.cssVar} strokeWidth={1.5} />
            </pattern>
          );
        }
        // crosshatch3
        return (
          <pattern key={id} id={id} width={3} height={3} patternUnits="userSpaceOnUse">
            <rect width={3} height={3} fill={spec.cssVar} fillOpacity={0.35} />
            <line x1={0} y1={0} x2={3} y2={3} stroke={spec.cssVar} strokeWidth={1} />
            <line x1={3} y1={0} x2={0} y2={3} stroke={spec.cssVar} strokeWidth={1} />
          </pattern>
        );
      })}
    </defs>
  );
}

/** Resolves a band spec to the SVG fill value: the solid colour, the
 * pattern url(), or "none" for the outline-only "no data" band. */
export function bandFill(spec: BandSpec): string {
  if (spec.pattern === "solid") return spec.cssVar;
  if (spec.pattern === "dashed") return "none";
  return `url(#band-hatch-${spec.token})`;
}
