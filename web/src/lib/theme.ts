import { create } from "zustand";

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-theme", t);
}

// Live Operations defaults dark, Analytics/Reports defaults light
// (UX-APPFLOW.md §20/§24). Pages call setTheme on mount.
export const useThemeStore = create<ThemeState>((set) => ({
  theme: "light",
  setTheme: (t) => {
    applyTheme(t);
    set({ theme: t });
  },
}));
