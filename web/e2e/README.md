# E2E demo walkthrough

MVP-PLAN.md §3.5's "Playwright E2E demo script + rehearsal" -- a real
Chromium browser driving the real dashboard against the real Docker
backend through PRD.md §16.2's seven-step jury demo script, not a mock
of any of it.

## Run

```bash
# from backend/
docker compose up -d --build
# from web/, in a separate terminal/tab (Vite dev server on :5173)
npm run dev
# from web/, once both are up
npx playwright test
```

All 7 steps pass as of 2026-08-25.

## What each step actually verifies

PRD §16.2's seven steps assume a phone on stage and a physical shake
rig. This suite drives the *dashboard* half of that demo for real, and
substitutes a labelled software proxy for the two steps that need
physical hardware:

1. **Risk map colours a stretch High under live rain** -- real: sets the
   Risk Map condition simulator to rain + low visibility + high traffic
   and asserts a real `H`/`S` band segment renders in the Top-N table,
   scored by the actual model (`GET /risk/bbox` with real overrides).
2. **Trigger a crash** -- software proxy for the shake rig: clicks
   Simulator Console's real "Inject crash" button, which POSTs to
   `/v1/sim/crash` and runs the actual ingest pipeline. PRD's own text
   already allows this ("via a controlled shake rig (**or the
   simulator, labelled as such**)").
3. **Alert appears within 20 seconds** -- real, and measured with an
   actual clock, not a generous retry window: a *second*, already-open
   browser page (opened once in `beforeAll`, standing in for the "app
   running" dashboard PRD's own stage direction assumes) receives the
   alert over the live WebSocket and the test asserts the elapsed time
   from the moment step 2's `POST /sim/crash` fired. See "Two pages, not
   one" below for why this matters.
4. **Simulated dispatch ticket, SIMULATED banner** -- real: opens
   Incident Detail and asserts the Simulation Seal's exact text. The
   "one-line config that swaps it for a real gateway" PRD asks the
   presenter to show is `backend/app/config.py`'s `gateway` setting
   (`RRX_GATEWAY` env var) -- a code fact, not a dashboard element, so
   it's stated here rather than asserted in the browser.
5. **Airplane mode + SMS path** -- software proxy for airplane mode
   (Playwright can't toggle a real device's radio state): toggles
   Simulator Console's channel to SMS, which routes through the actual
   RRX1 encode → parse → ingest round trip
   (`backend/app/services/sms_protocol.py`/`sms_ingest.py`), not a
   shortcut that just labels a normal alert differently. What the demo
   moment is really claiming -- the SMS transport path works -- is
   proven; the literal act of enabling airplane mode on a phone is not
   something this suite touches.
6. **Metrics panel** -- real: asserts Analytics' Response Performance
   and Channel Mix panels render, AND asserts Detection Quality shows
   `Not available (live)` -- proving the honest gap (no live cancel-rate
   source) is what actually renders, not a silently-invented number and
   not a panel that quietly vanished.
7. **Analyst view vs. official blackspot list** -- verified as *honestly
   disabled*, not working: Comparison mode doesn't exist (see
   `backend/README.md`'s and `MVP-PLAN.md` §3.4's real-data
   investigation -- no geolocatable MoRTH-iRAD/SaveLIFE-ZFC dataset was
   ever obtained), so this step asserts the toolbar button is disabled
   with the real reason in its tooltip, not that a comparison renders.

## Two pages, not one

`demo-walkthrough.spec.ts` opens two pages in `beforeAll`:
`dashboardPage`, opened once and left running for the whole suite, and
`triggerPage`, where every step's own action happens (Risk Map,
Simulator, Analytics). This isn't incidental -- it's the fix for a real
bug this suite's own first version had.

A naive version did `page.goto("/")` fresh inside step 3, then measured
time-to-visible from there. That measures **cold page-load time**: the
initial `GET /alerts` list fetch plus the first paint of however many
incident cards this dev database happens to have accumulated (hundreds,
after a long project session of repeated `/sim/crash` calls) -- not
what PRD §16.2 step 3 or the WebSocket architecture actually claims.
The real claim, and the one `backend/README.md`'s own verification
notes already made ("a `curl`'d `/sim/crash` appeared in the rail with
no page reload"), is about **live push latency to a dashboard that's
already open** -- exactly what PRD's own stage direction assumes
("Phone on stage, app running..." -- the screen is live *before*
anything is triggered). Opening `dashboardPage` once, before any alert
exists, and asserting against it after the trigger measures that real
claim: in this session's runs, the alert appeared in under 2 seconds on
an already-open dashboard, not 20.

## Known flakiness, and what's real vs. environmental

Getting step 1 to pass reliably took three iterations, all logged here
because two of the three revealed something real about the system this
suite runs against, not just test-script mistakes:

- **`GET /risk/bbox` has no per-request batching** (unlike the newer
  `GET /risk/heatgrid`) and blocks the backend's single event loop for
  its whole duration. Clicking multiple condition-simulator toggles in
  quick succession fires overlapping fetches that **serialize on the
  backend**, not in parallel -- three quick clicks can take three times
  as long as one, unpredictably. The current script waits for each
  fetch to visibly settle (`re-scoring…` disappearing) before firing
  the next condition change, rather than stacking clicks.
- **A single condition is a fragile assertion base.** Rain alone put
  exactly 1 of 1000 segments into the High band in this session's own
  measurement -- correct, but too thin a margin to assert on reliably
  run over run. Stacking rain + low visibility + high traffic (the same
  combination verified earlier in this project's own condition-
  simulator work) produced 329 High + 1 Severe of 1000, a real,
  comfortable margin.
- **Docker Desktop crashed repeatedly on this development machine** during
  the session that built this suite (a known, separately-documented
  stale-socket issue, not anything to do with this code) and took the
  backend down mid-test more than once, which looked like test flakiness
  before it was traced to the daemon itself being down. If this suite
  seems to hang or time out, check `docker ps` before assuming the test
  or the app regressed.
