from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.gateways import get_gateway
from app.gateways.base import DispatchGateway
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResponse
from app.services.alerts import ingest_alert

log = structlog.get_logger()
router = APIRouter(tags=["alerts"])


@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_alert(
    payload: AlertCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    gateway: DispatchGateway = Depends(get_gateway),
) -> AlertResponse:
    """PRD §10.1/§10.4: primary crash-alert ingest, idempotent on
    `alert_uuid`, and never returns a non-retryable error for a well-formed
    payload -- see app/services/alerts.py for the degrade-on-failure design.
    """
    return await ingest_alert(db, redis, gateway, payload)


@router.get("/alerts/{alert_uuid}", response_model=AlertResponse)
async def get_alert(alert_uuid: UUID, db: AsyncSession = Depends(get_db)) -> AlertResponse:
    """PRD §10.1: 'Status + dispatch state'. Unlike POST /alerts (whose
    `status` field is always the literal "RECEIVED" from PRD §10.1's worked
    example -- it signals ingest-acceptance, matching HTTP 202 semantics),
    this endpoint reports the alert's ACTUAL current status, since reporting
    the true state is this endpoint's entire purpose.
    """
    row = (await db.execute(select(Alert).where(Alert.alert_uuid == alert_uuid))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return AlertResponse(
        alert_uuid=row.alert_uuid,
        status=row.status.value,
        segment_id=row.segment_id,
        landmark=row.landmark,
        risk_context=None,
        dispatch=None,
        nearest_units=[],
    )
