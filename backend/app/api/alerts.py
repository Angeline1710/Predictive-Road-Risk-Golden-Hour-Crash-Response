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
from app.ml.risk_model import features_from_segment
from app.ml.risk_model import predict as predict_risk
from app.models.alert import Alert, AlertEvent
from app.models.dispatch import Dispatch
from app.models.road import RoadSegment
from app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertSummary,
    ConditionsOut,
    DispatchInfo,
    MotionOut,
    RiskContext,
    TimelineEventOut,
)
from app.services.alerts import ingest_alert

# Same window app/ml/risk_model.py's own feature engineering uses for
# `is_night` -- one definition, read twice, not two definitions that could
# quietly drift apart.
NIGHT_HOURS = set(range(0, 6)) | set(range(21, 24))

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
    the true state is this endpoint's entire purpose. UX-APPFLOW.md §22's
    Incident Detail is this endpoint's one real consumer, which is why it
    now returns the full row -- motion, conditions, dispatch, and the real
    `alert_events` timeline -- not just the four fields the rail needs.
    """
    row = (await db.execute(
        select(Alert, func.ST_Y(Alert.geom).label("lat"), func.ST_X(Alert.geom).label("lon"))
        .where(Alert.alert_uuid == alert_uuid)
    )).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="alert not found")
    alert = row.Alert

    # Latest dispatch attempt, if any -- mirrors list_alerts' subquery, just
    # scoped to one alert instead of a distinct-per-alert batch.
    dispatch_row = (await db.execute(
        select(Dispatch).where(Dispatch.alert_uuid == alert_uuid).order_by(Dispatch.requested_at.desc()).limit(1)
    )).scalar_one_or_none()
    dispatch = (
        DispatchInfo(gateway=dispatch_row.gateway, is_simulated=dispatch_row.is_simulated,
                     ticket_id=dispatch_row.external_ticket_id, eta_note=None)
        if dispatch_row is not None else None
    )

    # top_factors isn't a persisted column (only score/band are) -- recomputed
    # from the same (segment, occurred_at) the ingest-time score was computed
    # from, so it reproduces what actually drove that stored score rather
    # than a fresh "as of now" evaluation of a segment whose time-of-day
    # features have since moved on.
    risk_context: RiskContext | None = None
    if alert.segment_id is not None and alert.risk_score is not None:
        seg = (await db.execute(
            select(RoadSegment).where(RoadSegment.segment_id == alert.segment_id)
        )).scalar_one_or_none()
        if seg is not None:
            result = predict_risk(features_from_segment(seg, alert.occurred_at))
            risk_context = RiskContext(score=alert.risk_score, band=alert.risk_band, top_factors=result.top_factors)

    conditions = alert.conditions or {}
    is_night = alert.occurred_at.hour in NIGHT_HOURS
    timeline_rows = (await db.execute(
        select(AlertEvent).where(AlertEvent.alert_uuid == alert_uuid).order_by(AlertEvent.at.asc())
    )).scalars().all()

    return AlertResponse(
        alert_uuid=alert.alert_uuid,
        status=alert.status.value,
        severity=alert.severity.value,
        channel=alert.channel.value,
        occurred_at=alert.occurred_at,
        received_at=alert.received_at,
        is_simulated=alert.is_simulated,
        lat=row.lat,
        lon=row.lon,
        gps_accuracy_m=alert.gps_accuracy_m,
        has_trace=alert.has_trace,
        segment_id=alert.segment_id,
        landmark=alert.landmark,
        risk_context=risk_context,
        dispatch=dispatch,
        nearest_units=[],
        motion=MotionOut(
            speed_kmh=alert.speed_kmh, heading_deg=alert.heading_deg, peak_g=alert.peak_g,
            delta_v_kmh=alert.delta_v_kmh, impact_direction=alert.impact_direction,
            rollover=alert.rollover, still_moving=alert.still_moving,
        ),
        conditions=ConditionsOut(
            weather=conditions.get("weather"), visibility_m=conditions.get("visibility_m"),
            light="Night" if is_night else "Day", traffic_density=conditions.get("traffic_density"),
            conditions_available=conditions.get("conditions_available", False),
        ),
        occupant_hint=alert.occupant_hint,
        timeline=[
            TimelineEventOut(status=e.status.value, at=e.at, actor=e.actor) for e in timeline_rows
        ],
    )
