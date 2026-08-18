from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.gateways import get_gateway
from app.gateways.base import DispatchGateway
from app.models.alert import Alert
from app.models.dispatch import Dispatch
from app.schemas.alert import AlertCreate, AlertResponse, AlertSummary
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


@router.get("/alerts", response_model=list[AlertSummary])
async def list_alerts(
    since_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[AlertSummary]:
    """UX-APPFLOW.md §21.2: cold-start snapshot for the Live Operations
    incident rail. The WebSocket (`/ws/events`) carries live updates after
    load; this endpoint is only for populating the rail on first paint or
    reconnect, which is why it's a plain time-windowed list rather than
    anything paginated or filterable -- the rail only ever shows "recent".
    """
    since = datetime.now(UTC) - timedelta(hours=since_hours)
    # Most recent dispatch per alert, if any -- the rail shows a ticket_id
    # the moment one exists rather than waiting for a second round-trip.
    latest_dispatch = (
        select(Dispatch.alert_uuid, Dispatch.external_ticket_id)
        .distinct(Dispatch.alert_uuid)
        .order_by(Dispatch.alert_uuid, Dispatch.requested_at.desc())
        .subquery()
    )
    stmt = (
        select(
            Alert,
            func.ST_Y(Alert.geom).label("lat"),
            func.ST_X(Alert.geom).label("lon"),
            latest_dispatch.c.external_ticket_id,
        )
        .outerjoin(latest_dispatch, latest_dispatch.c.alert_uuid == Alert.alert_uuid)
        .where(Alert.received_at >= since)
        .order_by(Alert.received_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        AlertSummary(
            alert_uuid=row.Alert.alert_uuid,
            status=row.Alert.status.value,
            severity=row.Alert.severity.value,
            channel=row.Alert.channel.value,
            occurred_at=row.Alert.occurred_at,
            received_at=row.Alert.received_at,
            lat=row.lat,
            lon=row.lon,
            segment_id=row.Alert.segment_id,
            landmark=row.Alert.landmark,
            risk_score=row.Alert.risk_score,
            risk_band=row.Alert.risk_band,
            is_simulated=row.Alert.is_simulated,
            has_trace=row.Alert.has_trace,
            ticket_id=row.external_ticket_id,
        )
        for row in rows
    ]


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
