/** The product's signature loading/live-refresh motion (UX-APPFLOW.md §8.4)
 * -- replaces the generic skeleton shimmer everywhere in the product.
 * Drop inside a `position: relative; overflow: hidden` container. */
export function HeadlightSweep() {
  return (
    <div
      aria-hidden
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        width: 120,
        background: "linear-gradient(102deg, transparent 0%, rgba(232,151,28,0.08) 50%, transparent 100%)",
        animation: "headlight-sweep 1300ms linear infinite",
        pointerEvents: "none",
      }}
    />
  );
}
