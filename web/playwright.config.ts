import { defineConfig, devices } from "@playwright/test";

/** MVP-PLAN.md §3.5's "Playwright E2E demo script + rehearsal" -- a real
 * browser driving the dashboard through PRD.md §16.2's seven-step jury
 * walkthrough. See e2e/README.md for what each step actually verifies
 * and which two steps (2, 5) are software-side proxies for something
 * physical (a shake rig, airplane mode) Playwright can't touch.
 *
 * Requires the backend Docker stack already running (`docker compose up
 * -d --build` from backend/) -- unlike the frontend dev server below,
 * Playwright's webServer isn't a good fit for a multi-container Postgres
 * + Redis + migrations stack that takes real time to become healthy.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,   // the demo steps share state (an injected alert) across tests
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 30_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
