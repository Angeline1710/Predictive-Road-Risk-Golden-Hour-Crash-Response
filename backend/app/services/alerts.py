"""Orchestrates POST /alerts: the whole PRD §6.3.2 "processing engine" list
(validate -> dedup -> enrich -> persist -> route) for the DATA channel.

PRD §10.4's "never reject a well-formed payload" rule is enforced here, not
just at the transport layer: every enrichment step is best-effort and wrapped
so a failure degrades the response rather than raising past this function.
An emergency-alert endpoint that can say "no" is a design bug (PRD §10.4).
"""
from __future__ import annotations

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateways.base import DispatchGateway, GatewayRejected, GatewayTimeout
from app.models.alert import Alert, AlertChannel, AlertEvent, AlertStatus
from app.models.dispatch import Dispatch
from app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    DispatchInfo,
    NearestUnit,
    RiskContext,
)
from app.schemas.dispatch import (
    DispatchContact,
    DispatchEvidence,
    DispatchLocation,
    DispatchPayload,
)
from app.services import responders, segments

log = structlog.get_logger(__name__)


async def _append_event(db: AsyncSession, alert_uuid, status: AlertStatus,
                        actor: str, detail: dict | None = None) -> None:
    db.add(AlertEvent(alert_uuid=alert_uuid, status=status, actor=actor, detail=detail))


async def handle_alert(db: AsyncSession, gateway: DispatchGateway, body: AlertCreate) -> AlertResponse:
    # ---- idempotency: PRD 10.1 "Idempotent on alert_uuid" ------------------
    # A retry must not re-run enrichment or fire a second dispatch call --
    # that would create a duplicate incident ticket for one crash. Re-derive
    # nearest_units (cheap, deterministic, side-effect-free) from the alert's
    # already-stored geometry rather than re-running the whole pipeline.
    existing = await db.get(Alert, body.alert_uuid)
    if existing is not None:
        log.info("alerts.duplicate", alert_uuid=str(body.alert_uuid))
        lon_lat = (await db.execute(
            select(func.ST_X(Alert.geom), func.ST_Y(Alert.geom)).where(Alert.alert_uuid == existing.alert_uuid)
        )).first()
        nearest = []
        if lon_lat is not None:
            lon, lat = lon_lat
            nearest = await responders.find_nearest(db, lat, lon, limit=3)
        existing_dispatch = (await db.execute(
            select(Dispatch).where(Dispatch.alert_uuid == existing.alert_uuid)
            .order_by(Dispatch.requested_at.desc()).limit(1)
        )).scalar_one_or_none()
        return AlertResponse(
            alert_uuid=existing.alert_uuid, status=existing.status.value,
            segment_id=existing.segment_id, landmark=existing.landmark,
            risk_context=(RiskContext(score=existing.risk_score, band=existing.risk_band, top_factors=[])
                         if existing.risk_score is not None else None),
            dispatch=(DispatchInfo(gateway=existing_dispatch.gateway,
                                   is_simulated=existing_dispatch.is_simulated,
                                   ticket_id=existing_dispatch.external_ticket_id)
                     if existing_dispatch is not None else None),
            nearest_units=[NearestUnit(id=u.id, name=u.name, kind=u.kind, distance_km=u.distance_km)
                          for u in nearest],
        )

    # ---- persist immediately, before any enrichment --------------------
    # If enrichment or dispatch fails below, the alert is still durably
    # recorded with RECEIVED status -- exactly the "writes to a durable
    # queue and still returns 202" behaviour PRD 10.4 requires.
    alert = Alert(
        alert_uuid=body.alert_uuid,
        device_id=body.device_id,
        channel=AlertChannel.DATA,   # this endpoint IS the data channel; SMS comes via /ingest/sms
        status=AlertStatus.RECEIVED,
        severity=body.detection.severity,
        geom=f"SRID=4326;POINT({body.location.lon} {body.location.lat})",
        gps_accuracy_m=body.location.accuracy_m,
        occurred_at=body.occurred_at,
        speed_kmh=body.motion.speed_kmh,
        heading_deg=body.motion.heading_deg,
        peak_g=body.motion.peak_g,
        delta_v_kmh=body.motion.delta_v_kmh,
        impact_direction=body.motion.impact_direction,
        rollover=body.motion.rollover,
        still_moving=body.motion.still_moving,
        model_a_version=body.detection.model_version,
        is_simulated=body.is_simulated,
        has_trace=False,
    )
    db.add(alert)
    await _append_event(db, body.alert_uuid, AlertStatus.DETECTED, "device",
                        {"p_crash": body.detection.p_crash, "window": body.window.model_dump()})
    await _append_event(db, body.alert_uuid, AlertStatus.RECEIVED, "backend")
    await db.flush()

    # ---- enrichment: map-match, then whatever risk context is available ---
    # Weather/traffic live-feed enrichment (PRD 6.3.2 steps b/c) is NOT
    # implemented yet -- that needs the OpenWeatherMap/TomTom integrations
    # tracked separately in MVP-PLAN.md 3.2. Map-matching and risk-baseline
    # lookup need no external API and are implemented for real here.
    matched = None
    risk = None
    try:
        matched = await segments.match_point(db, body.location.lat, body.location.lon)
        if matched is not None:
            hour_bucket = body.occurred_at.weekday() * 24 + body.occurred_at.hour
            risk = await segments.current_risk(db, matched.segment_id, hour_bucket)
    except Exception:
        log.exception("alerts.enrichment_failed", alert_uuid=str(body.alert_uuid))
        # Degrade, don't raise -- PRD 10.4.

    landmark = None
    if matched is not None:
        landmark = f"{matched.road_class or 'road'} segment, {matched.district or matched.state or 'unknown area'}"
        alert.segment_id = matched.segment_id
        alert.landmark = landmark
    if risk is not None:
        alert.risk_score, alert.risk_band = risk
    alert.status = AlertStatus.ENRICHED
    await _append_event(db, body.alert_uuid, AlertStatus.ENRICHED, "backend",
                        {"segment_id": matched.segment_id if matched else None})

    # ---- nearest responders, for the response and for dispatch -----------
    nearest = []
    try:
        nearest = await responders.find_nearest(db, body.location.lat, body.location.lon, limit=3)
    except Exception:
        log.exception("alerts.nearest_lookup_failed", alert_uuid=str(body.alert_uuid))

    # ---- dispatch: PRD §11, failure here degrades, never rejects ---------
    dispatch_info = None
    payload = DispatchPayload(
        reported_at=body.occurred_at,
        confidence=body.detection.p_crash,
        location=DispatchLocation(
            lat=body.location.lat, lon=body.location.lon, accuracy_m=body.location.accuracy_m,
            landmark=landmark, district=matched.district if matched else None,
            state=matched.state if matched else None,
        ),
        severity=body.detection.severity.value,
        evidence=DispatchEvidence(
            peak_g=body.motion.peak_g, delta_v_kmh=body.motion.delta_v_kmh,
            rollover=body.motion.rollover, post_impact_motion=body.motion.still_moving,
        ),
        contact=DispatchContact(
            msisdn_ref=f"dev:{str(body.device_id)[:8]}" if body.device_id else None,
            language=body.device_context.locale,
        ),
        simulated=True,   # PRD 11.1: hardcoded true in v1, no live gateway exists
    )
    try:
        ack = await gateway.submit(payload)
        db.add(Dispatch(
            alert_uuid=body.alert_uuid, gateway=ack.gateway, is_simulated=ack.is_simulated,
            external_ticket_id=ack.ticket_id, responder_unit_id=ack.responder_unit_id,
            request_payload=payload.model_dump(mode="json"), response_payload=ack.raw_response,
            latency_ms=ack.latency_ms,
        ))
        alert.status = AlertStatus.DISPATCHED
        await _append_event(db, body.alert_uuid, AlertStatus.DISPATCHED, "gateway-sim",
                            {"ticket_id": ack.ticket_id})
        dispatch_info = DispatchInfo(gateway=ack.gateway, is_simulated=ack.is_simulated,
                                     ticket_id=ack.ticket_id, eta_note=ack.eta_note)
    except (GatewayRejected, GatewayTimeout) as e:
        log.warning("alerts.dispatch_degraded", alert_uuid=str(body.alert_uuid), reason=str(e))
        db.add(Dispatch(
            alert_uuid=body.alert_uuid, gateway="SIMULATED_PM_RAHAT", is_simulated=True,
            external_ticket_id=None, request_payload=payload.model_dump(mode="json"),
            response_payload={"error": str(e)},
        ))
        alert.status = AlertStatus.FAILED
        await _append_event(db, body.alert_uuid, AlertStatus.FAILED, "backend", {"reason": str(e)})
        dispatch_info = DispatchInfo(gateway="SIMULATED_PM_RAHAT", is_simulated=True,
                                     ticket_id=None, eta_note="dispatch unavailable, retry queued")

    await db.commit()

    return AlertResponse(
        alert_uuid=body.alert_uuid,
        status=alert.status.value,
        segment_id=alert.segment_id,
        landmark=alert.landmark,
        risk_context=(RiskContext(score=alert.risk_score, band=alert.risk_band,
                                  top_factors=[]) if alert.risk_score is not None else None),
        dispatch=dispatch_info,
        nearest_units=[NearestUnit(id=u.id, name=u.name, kind=u.kind, distance_km=u.distance_km)
                      for u in nearest],
    )
