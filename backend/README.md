# rrx-api

Backend for Predictive Road-Risk & Golden-Hour Crash Response. Companion to
`../PRD.md` (§9 data model, §10 API spec, §11 gateway, §12.2 tech stack) --
that document is the source of truth; this README is just how to run it.

## Status

Scaffold + `POST /alerts` end to end, verified against real PostGIS/Redis via
Docker Compose (not mocked). Everything else in PRD §10 is not yet built --
see `../MVP-PLAN.md` §3.1 for the remaining endpoint list and effort estimate.

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
| `POST /alerts` | Real: persists, map-matches, dispatches, idempotent |
| `SimulatedPmRahatGateway` | Real state machine + PostGIS nearest-responder + injectable failure modes (`GatewayModeState`), per PRD §11.2 |
| Map-matching | Real PostGIS query against `road_segments` (empty until ETL) |
| Risk context | Reads `risk_baseline` if precomputed; **nightly precompute job not built** |
| Weather/traffic enrichment | **Not implemented** -- external API integration is separate scoped work (MVP-PLAN §3.2) |
| `/devices/register`, `/risk/*`, `/dashboard/*`, `/ws/events`, `/sim/*` | **Not implemented** -- PRD §10.1-10.3 lists them; none exist yet |
| Redis | Configured, not yet used (no caching/pub-sub wired up) |
| Auth | Not implemented -- every route is currently open |

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
alembic/         hand-written initial migration (0001), matches PRD §9 exactly
```
