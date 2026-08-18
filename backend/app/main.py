from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.alerts import router as alerts_router
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

app.include_router(alerts_router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
