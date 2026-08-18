import type { ReactNode } from "react";

export interface SimulationSealProps {
  ticketId: string | null;
  assignmentLine?: string;
  children?: ReactNode;
  className?: string;
}

/** Mandatory, non-dismissible treatment applied to every element
 * representing the simulated government gateway (UX-APPFLOW.md §7.5) --
 * design-level enforcement of PRD §11's simulation boundary. Deliberately
 * has no collapse/dismiss affordance: it must be impossible for a jury
 * member, an operator, or a screenshot to mistake simulated dispatch for
 * real dispatch. This is the one place `flare-500` red appears outside a
 * genuine failure. */
export function SimulationSeal({ ticketId, assignmentLine, children, className }: SimulationSealProps) {
  return (
    <div
      className={className}
      style={{
        border: "2px dashed var(--flare-500)",
        borderRadius: "var(--radius-md)",
        overflow: "hidden",
        background: "var(--surface)",
      }}
    >
      <div
        style={{
          height: 28,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          background:
            "repeating-linear-gradient(45deg, rgba(224,49,49,0.16) 0 4px, rgba(224,49,49,0.06) 4px 8px)",
          borderBottom: "1px dashed var(--flare-500)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-ui)",
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--flare-500)",
          }}
        >
          Simulated dispatch
        </span>
        <span style={{ fontSize: 11, color: "var(--ink-secondary)" }}>— no live government link</span>
      </div>

      <div style={{ padding: 12, fontFamily: "var(--font-telemetry)", fontSize: 13, color: "var(--ink-primary)" }}>
        <div>Ticket {ticketId ?? "pending"}</div>
        {assignmentLine && <div style={{ color: "var(--ink-secondary)", marginTop: 2 }}>{assignmentLine}</div>}
        {children}
      </div>
    </div>
  );
}
