from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from sqlalchemy import text

from app.api.alerts import router as alerts_router
from app.config import settings
from app.db import engine

logging.basicConfig(level=settings.log_level, format="%(message)s")
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)

app = FastAPI(
    title="rrx-api",
    summary="Predictive Road-Risk & Golden-Hour Crash Response -- backend API",
    version="0.1.0",
)

app.include_router(alerts_router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness + a real dependency check, not just 'the process is up'."""
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "gateway": settings.gateway}
