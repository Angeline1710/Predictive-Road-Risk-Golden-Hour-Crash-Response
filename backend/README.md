# rrx-api

Backend for Predictive Road-Risk & Golden-Hour Crash Response. Companion to
`../PRD.md` (§9 data model, §10 API spec, §11 gateway, §12.2 tech stack) --
that document is the source of truth; this README is just how to run it.

## Status

Functionally complete for MVP scope. Alert ingest (HTTPS + SMS), Model B risk
serving, device registration, the WebSocket event feed, and the `/sim/*` demo
endpoints all work end to end, verified against real PostGIS/Redis via Docker
Compose (not mocked) -- including live verification against the `web/`
dashboard's Live Operations view. What's left: vector tiles, `/risk/route`,
and dashboard-facing RBAC. See `../MVP-PLAN.md` §3.1 for the remainder.

## Run it

```bash
docker compose up --build
curl http://localhost:8000/health
```

The `api` container runs `alembic upgrade head` before starting `uvicorn`, so
a fresh `docker compose up` migrates the database automatically. Postgres
data persists in the `rrx_pgdata` volume across restarts.

## Local (non-Docker) development

```bash
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d postgres redis               # still need real Postgres/Redis
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Verifying `POST /alerts`

```bash
curl -X POST http://localhost:8000/v1/alerts -H "Content-Type: application/json" -d '{
  "alert_uuid": "9c1f7d3e-5b2a-4f18-9e77-2a4b6c8d0e11",
  "occurred_at": "2026-08-14T18:32:11.482+05:30",
  "location": {"lat": 12.91845, "lon": 80.22456, "accuracy_m": 8.0},
  "motion": {"speed_kmh": 68.4, "heading_deg": 142.0, "peak_g": 9.1,
             "delta_v_kmh": 41.2, "impact_direction": "front",
             "rollover": false, "still_moving": false},
  "detection": {"p_crash": 0.93, "severity": "SEVERE", "model_version": "model_a_v1.3"},
  "window": {"duration_s": 10, "outcome": "EXPIRED"},
  "is_simulated": true
}'
```

Returns `202` with a simulated dispatch (`ticket_id`, `SIM-YYYY-MMDD-NNNNNN`).
`segment_id`/`landmark`/`nearest_units` populate once `road_segments` and
`responder_units` are seeded (ETL not yet run -- MVP-PLAN.md §3.2); until
then they degrade to `null`/`[]`, which is the intended behaviour (PRD §10.4),
not a bug.

Retrying the same `alert_uuid` is idempotent -- no duplicate row, no second
call to the dispatch gateway.

## What's real vs. stubbed

| Piece | Status |
|---|---|
| Schema (14 tables, PRD §9) | Real, migrated, verified |
| `POST /alerts`, `GET /alerts/{uuid}`, `GET /alerts` (list) | Real: persists, map-matches, scores, dispatches, idempotent. List endpoint is a cold-start snapshot for the dashboard rail, not paginated -- see its docstring. `GET /alerts/{uuid}` (2026-08-24) now returns the full row for `web/`'s Incident Detail view -- motion, conditions, the real `alert_events` timeline, `top_factors` (recomputed from the stored segment/time, since only score/band are persisted columns) -- not just the four rail fields it returned before |
| `POST /ingest/sms` | Real: parses the RRX1 wire protocol, CRC-checks, mirrors the HTTPS ingest pipeline. The PRD's own worked-example CRC doesn't reproduce under CRC-8/ATM or 9 other tested variants -- documented in `app/services/sms_protocol.py` as a PRD placeholder-text issue, not a bug here |
| `GET /risk/point`, `GET /risk/bbox` | Real: loads `risk_model_v1.txt` (LightGBM), returns score/band/SHAP top-3 **and segment geometry** (added for the dashboard's map overlay). `/risk/route`, `/risk/tiles` still absent -- left unimplemented rather than stubbed with fake data |
| `SimulatedPmRahatGateway` | Real state machine + PostGIS nearest-responder + injectable failure modes (`GatewayModeState`), per PRD §11.2 |
| `POST /devices/register`, `POST /devices/{id}/heartbeat`, `GET /devices/count` | Real. Heartbeat is the only route gated by device JWT so far |
| `WS /ws/events` | Real Redis pub/sub fan-out, verified live against the dashboard (a `curl`'d `/sim/crash` appeared in the rail with no page reload) |
| `/sim/*` | Real, env-flag gated (`RRX_DEMO_MODE`) |
| Map-matching | Real PostGIS query against `road_segments`, populated by the ETL (`../etl/`) |
| Weather/traffic enrichment | Map-match is real; weather/traffic external API calls honestly degrade to "unavailable" -- no API key configured, by design not oversight |
| `/risk/route`, `/risk/tiles`, dashboard-facing RBAC | **Not implemented.** Device JWT exists; there is no operator/analyst login, so every dashboard-facing route is open |
| Redis | Used for alert dedup (SETNX), the durable never-reject fallback queue, and WS pub/sub |

## Repository layout

Matches PRD §12.6:

```
app/
├── api/        FastAPI routers
├── services/    business logic (alerts.py, segments.py, responders.py)
├── gateways/    DispatchGateway protocol + SimulatedPmRahatGateway
├── models/      SQLAlchemy + GeoAlchemy2
├── schemas/     Pydantic request/response
├── ml/          (empty -- Model B serving not wired up yet)
└── workers/     (empty -- nightly precompute not built yet)
alembic/         hand-written initial migration (0001, matches PRD §9 exactly)
                 + 0002 (alerts.occupant_hint, for web/'s Incident Detail)
```
