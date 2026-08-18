"""PRD §6.3.2: validate -> dedup -> enrich -> score -> persist -> route ->
broadcast. And PRD §10.4: this path never returns a non-retryable error for
a well-formed payload.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateways.base import DispatchGateway, GatewayRejected, GatewayTimeout
from app.ml.risk_model import features_from_segment
from app.ml.risk_model import predict as predict_risk
from app.models.alert import Alert, AlertChannel, AlertEvent, AlertStatus
from app.models.dispatch import Dispatch
from app.models.road import RoadSegment
from app.schemas.alert import AlertCreate, AlertResponse, DispatchInfo, NearestUnit, RiskContext
from app.schemas.dispatch import (
    DispatchContact,
    DispatchEvidence,
    DispatchLocation,
    DispatchPayload,
    VictimHint,
)
from app.services.enrichment import enrich
from app.services.events import publish_event
from app.services.responders import find_nearest

log = structlog.get_logger()

DEDUP_TTL_S = 3600           # PRD §6.3.2 step 2: Redis SETNX, 1h TTL
PENDING_QUEUE_KEY = "rrx:alerts:pending_persist"   # PRD §10.4 durable fallback


async def _record_event(db: AsyncSession, alert_uuid, status: AlertStatus, actor: str,
                        detail: dict | None = None) -> None:
    db.add(AlertEvent(alert_uuid=alert_uuid, status=status, actor=actor, detail=detail))


async def _existing_response(db: AsyncSession, alert_uuid) -> AlertResponse | None:
    """Idempotent replay (PRD §10.1): if this alert_uuid was already
    processed, return the same shape rather than reprocessing it.
    """
    row = (await db.execute(select(Alert).where(Alert.alert_uuid == alert_uuid))).scalar_one_or_none()
    if row is None:
        return None
    return AlertResponse(
        alert_uuid=row.alert_uuid,
        status="RECEIVED",
        segment_id=row.segment_id,
        landmark=row.landmark,
        risk_context=(
            RiskContext(score=row.risk_score, band=row.risk_band, top_factors=[])
            if row.risk_score is not None else None
        ),
        dispatch=None,   # dispatch detail isn't reconstructed on replay in this scaffold
        nearest_units=[],
    )


async def ingest_alert(
    db: AsyncSession, redis: Redis, gateway: DispatchGateway, payload: AlertCreate,
) -> AlertResponse:
    # ---- 2. Deduplicate --------------------------------------------------
    dedup_key = f"rrx:alert:{payload.alert_uuid}"
    is_new = await redis.set(dedup_key, "1", ex=DEDUP_TTL_S, nx=True)
    if not is_new:
        existing = await _existing_response(db, payload.alert_uuid)
        if existing is not None:
            log.info("alerts.duplicate", alert_uuid=str(payload.alert_uuid))
            return existing
        # Redis says seen, DB disagrees (e.g. Redis restarted mid-flight) --
        # fall through and process it for real rather than returning nothing.

    # ---- 5a. Persist (initial RECEIVED row) -------------------------------
    # PRD §10.4: a persistence failure here still returns 202. The durable
    # fallback is a Redis queue -- simple, but real: nothing is silently
    # dropped, and a worker can drain rrx:alerts:pending_persist later.
    point = ST_SetSRID(ST_MakePoint(payload.location.lon, payload.location.lat), 4326)
    alert_row = Alert(
        alert_uuid=payload.alert_uuid,
        device_id=payload.device_id,
        channel=AlertChannel.DATA,
        status=AlertStatus.RECEIVED,
        severity=payload.detection.severity,
        geom=point,
        gps_accuracy_m=payload.location.accuracy_m,
        occurred_at=payload.occurred_at,
        speed_kmh=payload.motion.speed_kmh,
        heading_deg=payload.motion.heading_deg,
        peak_g=payload.motion.peak_g,
        delta_v_kmh=payload.motion.delta_v_kmh,
        impact_direction=payload.motion.impact_direction,
        rollover=payload.motion.rollover,
        still_moving=payload.motion.still_moving,
        model_a_version=payload.detection.model_version,
        is_simulated=payload.is_simulated,
        has_trace=False,
    )
    try:
        db.add(alert_row)
        await db.flush()
        await _record_event(db, payload.alert_uuid, AlertStatus.RECEIVED, "backend")
        await db.commit()
        await publish_event(redis, "alert.created", {
            "alert_uuid": str(payload.alert_uuid), "severity": payload.detection.severity.value,
            "lat": payload.location.lat, "lon": payload.location.lon, "channel": "DATA",
        })
    except Exception as e:  # noqa: BLE001 -- must degrade, never raise past here
        await db.rollback()
        log.error("alerts.persist.failed_falling_back_to_queue", error=str(e))
        await redis.lpush(PENDING_QUEUE_KEY, payload.model_dump_json())
        return AlertResponse(alert_uuid=payload.alert_uuid, status="RECEIVED")

    # ---- 3. Enrich ---------------------------------------------------------
    enrichment = await enrich(db, redis, payload.location.lat, payload.location.lon)
    alert_row.segment_id = enrichment.segment_id
    alert_row.landmark = enrichment.landmark
    alert_row.conditions = {
        "weather": enrichment.weather,
        "visibility_m": enrichment.visibility_m,
        "conditions_available": enrichment.conditions_available,
        "degraded_reasons": enrichment.degraded_reasons,
    }
    alert_row.status = AlertStatus.ENRICHED
    await _record_event(db, payload.alert_uuid, AlertStatus.ENRICHED, "backend",
                        detail={"degraded_reasons": enrichment.degraded_reasons})

    # ---- 4. Score: Model B, only if map-matching found a segment ----------
    # No fabricated score when there is no segment -- matches app/api/risk.py's
    # honest-404 posture rather than inventing a number for an unmatched point.
    risk_context: RiskContext | None = None
    if enrichment.segment_id is not None:
        seg = (await db.execute(
            select(RoadSegment).where(RoadSegment.segment_id == enrichment.segment_id)
        )).scalar_one_or_none()
        if seg is not None:
            risk = predict_risk(features_from_segment(seg, payload.occurred_at))
            alert_row.risk_score = risk.score
            alert_row.risk_band = risk.band
            alert_row.model_b_version = risk.model_version
            risk_context = RiskContext(score=risk.score, band=risk.band, top_factors=risk.top_factors)

    await db.commit()

    # ---- 6. Route: nearest responders + dispatch gateway --------------------
    nearest = await find_nearest(db, payload.location.lat, payload.location.lon, limit=3)
    nearest_units = [
        NearestUnit(id=n.id, name=n.name, kind=n.kind, distance_km=n.distance_km) for n in nearest
    ]

    dispatch_info: DispatchInfo | None = None
    dispatch_payload = DispatchPayload(
        reported_at=payload.occurred_at,
        confidence=payload.detection.p_crash,
        location=DispatchLocation(
            lat=payload.location.lat, lon=payload.location.lon,
            accuracy_m=payload.location.accuracy_m, landmark=enrichment.landmark,
            district=enrichment.district, state=enrichment.state,
        ),
        severity=payload.detection.severity.value,
        evidence=DispatchEvidence(
            peak_g=payload.motion.peak_g, delta_v_kmh=payload.motion.delta_v_kmh,
            rollover=payload.motion.rollover, post_impact_motion=payload.motion.still_moving,
        ),
        victim_hint=VictimHint(occupants_est=payload.occupant_hint),
        contact=DispatchContact(
            msisdn_ref=f"dev:{str(payload.device_id)[:8]}" if payload.device_id else None,
            language=payload.device_context.locale,
        ),
        pm_rahat_eligible=True,
        simulated=payload.is_simulated,
    )
    try:
        ack = await gateway.submit(dispatch_payload)
        db.add(Dispatch(
            alert_uuid=payload.alert_uuid, gateway=ack.gateway, is_simulated=ack.is_simulated,
            external_ticket_id=ack.ticket_id, responder_unit_id=ack.responder_unit_id,
            request_payload=json.loads(dispatch_payload.model_dump_json()),
            response_payload=ack.raw_response, latency_ms=ack.latency_ms,
            acknowledged_at=datetime.now(UTC),
        ))
        alert_row.status = AlertStatus.DISPATCHED
        await _record_event(db, payload.alert_uuid, AlertStatus.DISPATCHED, "gateway-sim",
                            detail={"ticket_id": ack.ticket_id})
        await db.commit()
        dispatch_info = DispatchInfo(
            gateway=ack.gateway, is_simulated=ack.is_simulated,
            ticket_id=ack.ticket_id, eta_note=ack.eta_note,
        )
        await publish_event(redis, "alert.status_changed", {
            "alert_uuid": str(payload.alert_uuid), "status": "DISPATCHED", "ticket_id": ack.ticket_id,
        })
    except (GatewayRejected, GatewayTimeout) as e:
        # PRD §11.2 point 7 / §10.4: the gateway misbehaving degrades the
        # response, it does not fail the ingest. The alert is safely
        # persisted and enriched regardless of what the gateway did --
        # FAILED here means "the dispatch attempt to the gateway failed",
        # not "the alert failed". It is a distinct failure surface from the
        # client-side channel exhaustion in UX-APPFLOW.md §18, which the
        # AlertStatus enum has no more specific state for.
        log.warning("alerts.dispatch.degraded", alert_uuid=str(payload.alert_uuid), error=str(e))
        alert_row.status = AlertStatus.FAILED
        await _record_event(db, payload.alert_uuid, AlertStatus.FAILED, "gateway-sim",
                            detail={"error": str(e)})
        await db.commit()
        await publish_event(redis, "alert.status_changed", {
            "alert_uuid": str(payload.alert_uuid), "status": "FAILED", "reason": str(e),
        })

    return AlertResponse(
        alert_uuid=payload.alert_uuid,
        status="RECEIVED",
        segment_id=enrichment.segment_id,
        landmark=enrichment.landmark,
        risk_context=risk_context,
        dispatch=dispatch_info,
        nearest_units=nearest_units,
    )
