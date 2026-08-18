from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_gateway
from app.gateways.base import DispatchGateway
from app.schemas.alert import AlertCreate, AlertResponse
from app.services.alerts import handle_alert

router = APIRouter(prefix="/v1", tags=["alerts"])


@router.post("/alerts", response_model=AlertResponse, status_code=202)
async def create_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
    gateway: DispatchGateway = Depends(get_gateway),
) -> AlertResponse:
    """PRD §10.1: primary crash-alert ingest. Idempotent on alert_uuid.

    Rate limiting is deliberately absent from this route. PRD §6.3.1: crash
    alerts get a much higher ceiling than everything else and are never
    hard-dropped -- a rate limiter must never be the reason an emergency
    alert fails. Ordinary endpoints get the default limiter (see main.py);
    this one is exempt by construction, not by a higher configured number.
    """
    return await handle_alert(db, gateway, body)
