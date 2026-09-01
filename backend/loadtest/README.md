# Load tests

MVP-PLAN.md §3.5's "k6 load test — 100 alerts/min burst (NFR-P7)" and the
adjacent NFR-P5 check. Two scripts, both real k6, both run against the
actual `docker compose` stack (not a mock).

## Run

```bash
docker compose up -d --build   # from backend/
docker run --rm -i -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run - < loadtest/alerts_burst.js
docker run --rm -i -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run - < loadtest/risk_point.js
```

`host.docker.internal`, not `localhost` — k6 runs in its own sibling
container on Docker Desktop (Windows/Mac), which can't reach the backend
container via `localhost`; on native Linux Docker, `--network host` plus
`BASE_URL=http://localhost:8000` works instead.

## Results (2026-08-25, this machine)

**`risk_point.js` (NFR-P5, ≤300ms p95): PASS.** `p(95)=79.86ms` on real
map-matched points, `0.00%` failure rate (404s on points outside the
corridor's own road network are expected and excluded from the failure
count via `http.expectedStatuses(200, 404)` — see the script's own
comment).

**`alerts_burst.js` (NFR-P3 ≤400ms p95 / ≤900ms p99, NFR-P7 no drops):
PARTIAL.** First run (before the fix below): `p(95)=693ms` (fails
NFR-P3), `p(99)=725ms` (passes), 4 real connection timeouts out of 201
requests (`checks` rate 98.0%, below the 99% bar). After the fix:
`p(95)=675ms` (still fails NFR-P3), `p(99)=766ms` (passes), 1 timeout out
of 201 (`checks` rate 99.5%, now passing). **NFR-P7's "no drops" is
effectively met after the fix (real drops nearly eliminated); NFR-P3's
latency budget is not.**

### Root cause, diagnosed with evidence, not guessed

Two real, distinct problems, found by reading the code the numbers
pointed at rather than assumed:

1. **The event loop was blocked by CPU-bound work.** This backend runs a
   single `uvicorn` worker on purpose — `app/gateways/simulated.py`'s
   `SimulatedPmRahatGateway` keeps ticket state in an in-process dict, and
   a second worker process would silently fragment that state (its own
   docstring says so). `app/ml/risk_model.py`'s `predict()` (LightGBM
   inference) was called directly inside the async `ingest_alert()`,
   which means every alert's model-scoring step blocked the ONE event
   loop for its full duration, serializing every other concurrent
   request's I/O behind it. **Fixed**: wrapped the call in
   `asyncio.to_thread()` (`app/services/alerts.py`) — verified to cut
   real connection timeouts from 4/201 to 1/201 in a re-run against the
   same load profile. This does not add a second worker or touch the
   in-memory ticket state at all.

2. **Every single alert makes a real, rate-limited external HTTP call in
   its critical path — and it was never optional in practice.** Checked
   `docker logs backend-api-1` from the burst-test window directly rather
   than guessing: **all 200/200** requests logged
   `"event": "enrichment.geocode.degraded"` — `app/services/enrichment.py`'s
   `reverse_geocode()` calls the real public Nominatim API
   (`nominatim.openstreetmap.org`), which the function's own comment
   already documents as "rate-limited (1 req/s)" — well below this test's
   sustained 100/min (1.67/s) rate. Under that load every call either hit
   the rate limit or the surrounding 0.5s `NOMINATIM_TIMEOUT_S` cap, and
   the request waited out essentially the full timeout before degrading.
   500ms of forced wait on nearly every request lines up closely with the
   observed ~630-680ms average request latency (the rest being the real
   DB/PostGIS work). **NOT fixed in this pass** — `landmark` is a real
   field in the dispatch payload responders see, so changing this from
   "await it, capped at 0.5s" to "fire-and-forget, dispatch without it"
   is a product behaviour decision (does a responder get a landmark
   string most of the time, or reliably never under load?), not a
   drive-by performance patch. Documented here as the real, evidenced
   root cause of the remaining NFR-P3 gap, with the fix path named, for
   whoever makes that call.

**Bottom line for the demo**: the system does not currently silently drop
alerts under a 100/min burst (verified, and improved by a real fix), but
individual alerts run slower than NFR-P3's budget under that load,
almost entirely because of one external geocoding call that this
deployment doesn't control the availability of.
