"""Turns a parsed RRX1 message into the same persisted-alert pipeline
services/alerts.py runs for the HTTPS channel: enrich, score, persist,
route to the (simulated) gateway. Deliberately mirrors that module's
structure rather than sharing code with it -- an SMS-origin alert carries
materially less data (no device_id, no model_version, no window/context),
so forcing it through the same AlertCreate schema would mean fabricating
fields the phone never actually sent.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.gateways.base import DispatchGateway, GatewayRejected, GatewayTimeout
from app.ml.risk_model import features_from_segment
from app.ml.risk_model import predict as predict_risk
from app.models.alert import Alert, AlertChannel, AlertEvent, AlertSeverity, AlertStatus
from app.models.dispatch import Dispatch
from app.models.road import RoadSegment
from app.schemas.alert import AlertResponse, DispatchInfo, NearestUnit, RiskContext
from app.schemas.dispatch import (
    DispatchContact,
    DispatchEvidence,
    DispatchLocation,
    DispatchPayload,
)
from app.services.enrichment import enrich
from app.services.events import publish_event
from app.services.responders import find_nearest
from app.services.sms_protocol import ParsedRRX1

log = structlog.get_logger()

DEDUP_TTL_S = 3600


async def ingest_sms(
    db: AsyncSession, redis: Redis, gateway: DispatchGateway, parsed: ParsedRRX1,
) -> AlertResponse:
    dedup_key = f"rrx:alert:{parsed.alert_uuid}"
    is_new = await redis.set(dedup_key, "1", ex=DEDUP_TTL_S, nx=True)
    if not is_new:
        log.info("sms.duplicate", alert_uuid=str(parsed.alert_uuid))
        return AlertResponse(alert_uuid=parsed.alert_uuid, status="RECEIVED")

    point = ST_SetSRID(ST_MakePoint(parsed.lon, parsed.lat), 4326)
    alert_row = Alert(
        alert_uuid=parsed.alert_uuid,
        device_id=None,   # SMS carries no device identity -- see sms_protocol.py
        channel=AlertChannel.SMS,
        status=AlertStatus.RECEIVED,
        severity=AlertSeverity(parsed.severity),
        geom=point,
        gps_accuracy_m=parsed.gps_accuracy_m,
        occurred_at=parsed.occurred_at,
        speed_kmh=parsed.speed_kmh,
        heading_deg=parsed.heading_deg,
        peak_g=parsed.peak_g,
        rollover=parsed.rollover,
        still_moving=parsed.still_moving,
        is_simulated=False,
        has_trace=False,   # PRD §6.2.1: SMS never carries the sensor trace
    )
    try:
        db.add(alert_row)
        await db.flush()
        db.add(AlertEvent(alert_uuid=parsed.alert_uuid, status=AlertStatus.RECEIVED,
                          actor="sms-gateway", detail={"unresponsive": parsed.unresponsive}))
        await db.commit()
        await publish_event(redis, "alert.created", {
            "alert_uuid": str(parsed.alert_uuid), "severity": parsed.severity,
            "lat": parsed.lat, "lon": parsed.lon, "channel": "SMS",
        })
    except Exception as e:  # noqa: BLE001 -- PRD §10.4: never reject
        await db.rollback()
        log.error("sms.persist.failed_falling_back_to_queue", error=str(e))
        await redis.lpush("rrx:alerts:pending_persist_sms", str(parsed))
        return AlertResponse(alert_uuid=parsed.alert_uuid, status="RECEIVED")

    enrichment = await enrich(db, redis, parsed.lat, parsed.lon)
    alert_row.segment_id = enrichment.segment_id
    alert_row.landmark = enrichment.landmark
    alert_row.status = AlertStatus.ENRICHED
    db.add(AlertEvent(alert_uuid=parsed.alert_uuid, status=AlertStatus.ENRICHED, actor="backend",
                      detail={"degraded_reasons": enrichment.degraded_reasons}))

    risk_context: RiskContext | None = None
    if enrichment.segment_id is not None:
        seg = (await db.execute(
            select(RoadSegment).where(RoadSegment.segment_id == enrichment.segment_id)
        )).scalar_one_or_none()
        if seg is not None:
            risk = predict_risk(features_from_segment(seg, parsed.occurred_at))
            alert_row.risk_score = risk.score
            alert_row.risk_band = risk.band
            alert_row.model_b_version = risk.model_version
            risk_context = RiskContext(score=risk.score, band=risk.band, top_factors=risk.top_factors)

    await db.commit()

    nearest = await find_nearest(db, parsed.lat, parsed.lon, limit=3)
    nearest_units = [NearestUnit(id=n.id, name=n.name, kind=n.kind, distance_km=n.distance_km)
                     for n in nearest]

    dispatch_info: DispatchInfo | None = None
    dispatch_payload = DispatchPayload(
        reported_at=parsed.occurred_at, confidence=1.0,   # SMS carries no p_crash; already confirmed
        location=DispatchLocation(lat=parsed.lat, lon=parsed.lon, accuracy_m=parsed.gps_accuracy_m,
                                  landmark=enrichment.landmark, district=enrichment.district,
                                  state=enrichment.state),
        severity=parsed.severity,
        evidence=DispatchEvidence(peak_g=parsed.peak_g, rollover=parsed.rollover,
                                  post_impact_motion=parsed.still_moving),
        contact=DispatchContact(msisdn_ref=None, language="en-IN"),
        pm_rahat_eligible=True, simulated=False,
    )
    try:
        ack = await gateway.submit(dispatch_payload)
        db.add(Dispatch(
            alert_uuid=parsed.alert_uuid, gateway=ack.gateway, is_simulated=ack.is_simulated,
            external_ticket_id=ack.ticket_id, responder_unit_id=ack.responder_unit_id,
            request_payload=json.loads(dispatch_payload.model_dump_json()),
            response_payload=ack.raw_response, latency_ms=ack.latency_ms,
            acknowledged_at=datetime.now(UTC),
        ))
        alert_row.status = AlertStatus.DISPATCHED
        db.add(AlertEvent(alert_uuid=parsed.alert_uuid, status=AlertStatus.DISPATCHED,
                          actor="gateway-sim", detail={"ticket_id": ack.ticket_id}))
        await db.commit()
        dispatch_info = DispatchInfo(gateway=ack.gateway, is_simulated=ack.is_simulated,
                                     ticket_id=ack.ticket_id, eta_note=ack.eta_note)
        await publish_event(redis, "alert.status_changed", {
            "alert_uuid": str(parsed.alert_uuid), "status": "DISPATCHED", "ticket_id": ack.ticket_id,
        })
    except (GatewayRejected, GatewayTimeout) as e:
        log.warning("sms.dispatch.degraded", alert_uuid=str(parsed.alert_uuid), error=str(e))
        alert_row.status = AlertStatus.FAILED
        db.add(AlertEvent(alert_uuid=parsed.alert_uuid, status=AlertStatus.FAILED,
                          actor="gateway-sim", detail={"error": str(e)}))
        await db.commit()
        await publish_event(redis, "alert.status_changed", {
            "alert_uuid": str(parsed.alert_uuid), "status": "FAILED", "reason": str(e),
        })

    return AlertResponse(
        alert_uuid=parsed.alert_uuid, status="RECEIVED", segment_id=enrichment.segment_id,
        landmark=enrichment.landmark, risk_context=risk_context, dispatch=dispatch_info,
        nearest_units=nearest_units,
    )
