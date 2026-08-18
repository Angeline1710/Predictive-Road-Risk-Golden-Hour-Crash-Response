from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.alerts import router as alerts_router
from app.api.devices import router as devices_router
from app.api.risk import router as risk_router
from app.api.sms import router as sms_router
from app.api.ws import router as ws_router
from app.config import settings

structlog.configure(processors=[structlog.processors.JSONRenderer()])
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    log.info("startup", gateway=settings.gateway, demo_mode=settings.demo_mode)
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title="RRX API",
    description="Predictive Road-Risk & Golden-Hour Crash Response -- backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# The rrx-ops dashboard (MVP-PLAN.md §3.4, not yet built) is a separate Vite
# origin talking to this API cross-origin -- without this, its very first
# fetch() fails a CORS preflight before a single dashboard line is written.
# Wide open only in demo_mode; a real deployment sets explicit origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.demo_mode else [],
    allow_credentials=False,   # "*" + credentials is disallowed by browsers anyway
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts_router, prefix="/v1")
app.include_router(devices_router, prefix="/v1")
app.include_router(risk_router, prefix="/v1")
app.include_router(sms_router, prefix="/v1")
app.include_router(ws_router, prefix="/v1")

if settings.demo_mode:
    # UX-APPFLOW.md §25: the /sim/* routes exist at all only in a demo
    # build -- importing and registering the router is itself the gate,
    # not a per-request check inside it.
    from app.api.sim import router as sim_router
    app.include_router(sim_router, prefix="/v1")
    log.warning("sim_routes.enabled", note="RRX_DEMO_MODE=true -- /v1/sim/* is live")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
