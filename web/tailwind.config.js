/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bitumen: {
          0: "var(--bitumen-000)", 50: "var(--bitumen-050)", 100: "var(--bitumen-100)",
          200: "var(--bitumen-200)", 300: "var(--bitumen-300)", 400: "var(--bitumen-400)",
          500: "var(--bitumen-500)",
        },
        paper: {
          0: "var(--paper-000)", 100: "var(--paper-100)", 200: "var(--paper-200)",
          300: "var(--paper-300)", 400: "var(--paper-400)",
        },
        sodium: {
          200: "var(--sodium-200)", 300: "var(--sodium-300)", 400: "var(--sodium-400)",
          500: "var(--sodium-500)", 600: "var(--sodium-600)", 700: "var(--sodium-700)",
        },
        highway: {
          300: "var(--highway-300)", 500: "var(--highway-500)",
          600: "var(--highway-600)", 700: "var(--highway-700)",
        },
        risk: {
          low: "var(--risk-low)", mod: "var(--risk-mod)",
          high: "var(--risk-high)", severe: "var(--risk-severe)", none: "var(--risk-none)",
        },
        flare: { 500: "var(--flare-500)", 100: "var(--flare-100)" },
        ink: {
          primary: "var(--ink-primary)", secondary: "var(--ink-secondary)",
          muted: "var(--ink-muted)", disabled: "var(--ink-disabled)", inverse: "var(--ink-inverse)",
        },
        ground: "var(--ground)", surface: "var(--surface)", border: "var(--border)",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        ui: ["Inter", "system-ui", "sans-serif"],
        telemetry: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "var(--radius-sm)", md: "var(--radius-md)", lg: "var(--radius-lg)",
      },
      transitionDuration: {
        fast: "var(--motion-fast)", base: "var(--motion-base)", emphasis: "var(--motion-emphasis)",
      },
    },
  },
  plugins: [],
};
