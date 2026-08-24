/** UX-APPFLOW.md §24: "All panels export as PNG and CSV." Shared by every
 * Analytics panel rather than reimplemented per-chart.
 */

/** Reads a CSS custom property's current resolved value (e.g. "#E8971C"
 * for --sodium-500). Chart SVGs use resolved literal colours, not
 * `var(--x)` strings, specifically so exportSvgAsPng's cloned/serialized
 * copy renders identically outside the live DOM -- a data: URL SVG loaded
 * into an <img> has no access to the page's :root custom properties, so a
 * literal var() reference would silently paint as black/transparent in
 * the exported PNG even though it looks correct on screen. */
export function resolveToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function exportSvgAsPng(svg: SVGSVGElement, filename: string, scale = 2): void {
  const width = svg.viewBox.baseVal.width || svg.clientWidth;
  const height = svg.viewBox.baseVal.height || svg.clientHeight;
  const bg = resolveToken("--surface") || "#ffffff";

  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));

  const xml = new XMLSerializer().serializeToString(clone);
  const svg64 = btoa(unescape(encodeURIComponent(xml)));
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = width * scale;
    canvas.height = height * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0, width, height);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  };
  img.src = `data:image/svg+xml;base64,${svg64}`;
}

export function downloadCsv(filename: string, header: string[], rows: (string | number | null)[][]): void {
  const csv = [header, ...rows]
    .map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
