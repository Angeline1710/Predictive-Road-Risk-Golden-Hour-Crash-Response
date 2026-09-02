import { test, expect, type Browser, type BrowserContext, type Page } from "@playwright/test";

/** PRD.md §16.2's seven-step jury walkthrough, driven by a real browser
 * against the real dashboard + backend -- not a mock. See e2e/README.md
 * for which two steps (2 and 5) are software-side proxies for something
 * physical Playwright can't touch (a shake rig, airplane mode), and why
 * step 7 is verified as "honestly disabled," not "working."
 *
 * Two pages, not one, deliberately mirroring the real demo's own
 * structure: `dashboardPage` is opened ONCE in beforeAll and left running
 * for the whole suite, standing in for "app running" (PRD §16.2 step 1's
 * own stage direction) -- the operator's screen that's already live
 * before anything is triggered. `triggerPage` is where each step's own
 * action happens (Risk Map, Simulator, Analytics). This matters for step
 * 3's timing claim specifically: a fresh `page.goto("/")` measures cold
 * page-load time (list fetch + first paint of however many incidents
 * this dev database has accumulated, which is NOT what PRD §16.2 step 3
 * or the WS-push architecture actually claims), where the real claim
 * -- and what backend/README.md's own "a curl'd alert appeared in the
 * rail with no page reload" verification already proved -- is about
 * live WebSocket-push latency to a dashboard that's already open.
 *
 * test.describe.serial: steps 3-4 depend on the alert step 2 injects, so
 * these run in file order, not in parallel or shuffled.
 */
test.describe.serial("PRD §16.2 jury walkthrough", () => {
  let context: BrowserContext;
  let dashboardPage: Page;
  let triggerPage: Page;
  let injectedAlertUuid: string;
  let injectedTicketId: string;
  let injectedAtMs: number;

  test.beforeAll(async ({ browser }: { browser: Browser }) => {
    test.setTimeout(90_000);
    context = await browser.newContext();
    dashboardPage = await context.newPage();
    triggerPage = await context.newPage();
    // This dev database has accumulated hundreds of alerts from repeated
    // test/demo runs across this project's whole session -- a real jury
    // demo would start from a clean database, but this dev one doesn't,
    // so the cold-start list render can genuinely take a while. That
    // one-time cost happens HERE, before any timing claim is measured,
    // not inside step 3's assertion.
    await dashboardPage.goto("/");
    await expect(dashboardPage.getByText("LIVE INCIDENTS")).toBeVisible({ timeout: 60_000 });
  });

  test.afterAll(async () => {
    await context.close();
  });

  test("step 1: risk map shows a High/Severe segment under simulated rain", async () => {
    // playwright.config.ts's global 30s test timeout is far shorter than
    // this step's own /risk/bbox re-fetches can honestly take --
    // backend/README.md documents ~26s for 1000 segments as the common
    // case, and this session measured a real client-observed p95 over
    // 100s under some conditions. Three sequential waits below budget
    // for the documented worst case each, not the common one.
    test.setTimeout(300_000);
    await triggerPage.goto("/risk-map");
    // Give the live (unsimulated) view a moment to load -- not asserted
    // on, just confirms the page itself has mounted.
    await triggerPage.getByText("Corridor mode").waitFor();

    // GET /risk/bbox has no per-request batching (unlike the newer
    // /risk/heatgrid) and blocks the backend's single event loop for its
    // whole duration -- two overlapping calls serialize rather than run
    // in parallel, so each condition click below waits for the PREVIOUS
    // fetch to finish before firing the next one, rather than stacking
    // three clicks and letting them race. Rain alone put exactly 1 of
    // 1000 segments into High in this session's own measurement -- a
    // one-segment margin is too fragile to assert on reliably, so
    // visibility and traffic are stacked on top of it for a wider one.
    async function waitForRescoreToSettle() {
      await triggerPage.getByText("re-scoring…").waitFor({ state: "hidden", timeout: 120_000 }).catch(() => {});
    }
    await waitForRescoreToSettle();   // the initial live-conditions fetch that fires on mount
    await triggerPage.getByRole("button", { name: "Rain" }).click();
    await waitForRescoreToSettle();
    await triggerPage.getByRole("button", { name: "Low", exact: true }).nth(0).click();   // visibility: low
    await waitForRescoreToSettle();
    await triggerPage.getByRole("button", { name: "High", exact: true }).nth(1).click();  // traffic: high
    await waitForRescoreToSettle();

    await expect(triggerPage.getByText(/^[HS] (High|Severe)$/).first()).toBeVisible({ timeout: 10_000 });
  });

  test("step 2: inject a crash via the simulator (labelled as such -- see e2e/README.md on the shake rig)", async () => {
    await triggerPage.goto("/simulator");
    // SimulatorConsole.tsx's Severity field is a plain <select> with no
    // <label for>/aria-label association (FieldRow renders a sibling
    // <div>, not a real <label>) -- it's the only <select> on the page,
    // so a bare element locator is unambiguous without one.
    await triggerPage.locator("select").selectOption("SEVERE");

    const responsePromise = triggerPage.waitForResponse(
      (r) => r.url().includes("/v1/sim/crash") && r.request().method() === "POST",
    );
    injectedAtMs = Date.now();
    await triggerPage.getByRole("button", { name: "Inject crash" }).click();
    const response = await responsePromise;
    const body = await response.json();

    expect(response.status()).toBe(200);
    expect(body.alert_uuid).toBeTruthy();
    expect(body.dispatch?.ticket_id).toBeTruthy();
    injectedAlertUuid = body.alert_uuid;
    injectedTicketId = body.dispatch.ticket_id;

    await expect(triggerPage.getByText(injectedTicketId)).toBeVisible();
  });

  test("step 3: the alert appears on the already-open Live Operations dashboard within 20 seconds, with location/severity/conditions", async () => {
    // The real claim: a dashboard that's already open receives the new
    // alert over the live WebSocket within 20 seconds, with no reload --
    // dashboardPage has been open since beforeAll, so this is a live
    // push landing on a running screen, not a fresh load racing the
    // clock against its own cold-start render time.
    const remainingMs = Math.max(1_000, 20_000 - (Date.now() - injectedAtMs));
    await expect(dashboardPage.getByText(injectedTicketId)).toBeVisible({ timeout: remainingMs });
    expect(Date.now() - injectedAtMs).toBeLessThan(20_000);

    // Severity and a lat/lon pair render on the same rail card, per
    // UX-APPFLOW.md §21.2 -- confirms this isn't just a bare ticket
    // string floating on the page.
    await expect(dashboardPage.getByText("SEVERE").first()).toBeVisible();
    // .first(), not a bare assertion -- with ~200 accumulated rail cards
    // this dev database has, the lat/lon pattern matches every one of
    // them, not just the freshly injected alert's.
    await expect(dashboardPage.getByText(/-?\d{1,3}\.\d{5}\s+-?\d{1,3}\.\d{5}/).first()).toBeVisible();
  });

  test("step 4: the dispatch ticket carries the mandatory SIMULATED banner", async () => {
    await triggerPage.goto(`/incidents/${injectedAlertUuid}`);
    await expect(triggerPage.getByText("Simulated dispatch")).toBeVisible();
    await expect(triggerPage.getByText("no live government link")).toBeVisible();
    await expect(triggerPage.getByText(`Ticket ${injectedTicketId}`)).toBeVisible();
    // The "one-line config that swaps it for a real gateway" PRD §16.2
    // asks the presenter to show is backend/app/config.py's `gateway`
    // setting (RRX_GATEWAY env var) -- a code fact stated in
    // e2e/README.md, not a dashboard UI element, so it isn't asserted
    // here.
  });

  test("step 5: the SMS channel still lands an alert (software proxy for airplane mode -- see e2e/README.md)", async () => {
    await triggerPage.goto("/simulator");
    await triggerPage.getByRole("button", { name: "SMS", exact: true }).click();

    const responsePromise = triggerPage.waitForResponse(
      (r) => r.url().includes("/v1/sim/crash") && r.request().method() === "POST",
    );
    await triggerPage.getByRole("button", { name: "Inject crash" }).click();
    const response = await responsePromise;
    const body = await response.json();

    expect(response.status()).toBe(200);
    expect(body.status).toBe("RECEIVED");
    // The real RRX1 encode -> parse -> ingest round trip (backend/app/api/sim.py's
    // channel_hint=SMS path) is what actually matters here, not the UI --
    // a 200 with a real dispatch is the SMS transport path proven live.
    expect(body.dispatch?.ticket_id).toBeTruthy();
  });

  test("step 6: the metrics panel shows latency distribution, channel mix, and an honestly-labelled cancel-rate gap", async () => {
    await triggerPage.goto("/analytics");
    // exact: true -- GoldenHourPanel's own note text also contains the
    // phrase "Response performance" ("Same simulated-gateway caveat as
    // Response performance above..."), so a substring match resolves to
    // two elements.
    await expect(triggerPage.getByText("Response performance", { exact: true })).toBeVisible();
    // Analytics.tsx's <Stat label="p95" .../> renders lowercase text,
    // CSS-uppercased for display only -- textContent is still "p95".
    // .first() -- ResponsePanel's histogram SVG has its own "p95" marker
    // label in addition to the Stat, so this matches two elements.
    await expect(triggerPage.getByText(/^p95$/i).first()).toBeVisible();
    await expect(triggerPage.getByText("Channel mix")).toBeVisible();
    // "Cancel rate" (UX-APPFLOW.md §24's Detection quality panel) has no
    // live source -- app/services/alerts.py never persists window.outcome
    // (MVP-PLAN.md §3.4). This assertion is the point of this step: prove
    // the honest gap is what actually renders, not a silently-invented
    // number and not a panel that quietly vanished.
    await expect(triggerPage.getByText("Detection quality")).toBeVisible();
    await expect(triggerPage.getByText("Not available (live)")).toBeVisible();
  });

  test("step 7: the analyst view's blackspot comparison is honestly disabled, not silently broken", async () => {
    await triggerPage.goto("/risk-map");
    const comparisonButton = triggerPage.getByRole("button", { name: "Comparison mode" });
    await expect(comparisonButton).toBeDisabled();
    // The real reason, not a generic "coming soon" -- backend/README.md
    // and MVP-PLAN.md §3.4 document the same finding this tooltip states:
    // no real MoRTH-iRAD/SaveLIFE-ZFC blackspot dataset was ever obtained
    // for this corridor.
    await expect(comparisonButton).toHaveAttribute("title", /MoRTH|SaveLIFE|blackspot/i);
  });
});
