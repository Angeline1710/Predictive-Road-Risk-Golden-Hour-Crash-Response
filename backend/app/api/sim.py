"""PRD §10.3 demo-only endpoints. Registered in app/main.py ONLY when
settings.demo_mode is True -- UX-APPFLOW.md §25: "In production builds the
nav item is absent, not disabled." Importing this router at all is itself
gated, not just its behaviour.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.gateways import gateway_mode_state, get_gateway
from app.gateways.base import DispatchGateway
from app.gateways.simulated import GatewayMode
from app.models.alert import AlertSeverity
from app.schemas.alert import AlertCreate, AlertResponse, DeviceContext, Detection, Location, Motion, Window
from app.services.alerts import ingest_alert
from app.services.sms_ingest import ingest_sms
from app.services.sms_protocol import encode_rrx1, parse_rrx1

router = APIRouter(prefix="/sim", tags=["simulator"])

# NH-45 near Guduvancheri toll, Chengalpattu -- the PRD's own worked example
# location (PRD §10.1) and the frozen demo corridor (MVP-PLAN.md §2③).
DEMO_LAT, DEMO_LON = 12.91845, 80.22456


class SimCrashRequest(BaseModel):
    lat: float = Field(default=DEMO_LAT, ge=-90, le=90)
    lon: float = Field(default=DEMO_LON, ge=-180, le=180)
    severity: AlertSeverity = AlertSeverity.SEVERE
    speed_kmh: float = 68.4
    peak_g: float = 9.1
    # PRD §16.2 step 5 -- "phone in airplane mode, alert still lands via SMS"
    # -- is called out as the single most persuasive demo moment. "SMS" here
    # routes the synthetic crash through the ACTUAL RRX1 encode/parse/ingest
    # path (app/services/sms_protocol.py + sms_ingest.py), not a shortcut
    # that merely labels a normal alert differently, so the demo exercises
    # the real fallback channel.
    channel_hint: str = Field(default="DATA", pattern="^(DATA|SMS)$")


class GatewayModeRequest(BaseModel):
    mode: GatewayMode


@router.post("/crash", response_model=AlertResponse)
async def sim_crash(
    req: SimCrashRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    gateway: DispatchGateway = Depends(get_gateway),
) -> AlertResponse:
    """UX-APPFLOW.md §25: inject a synthetic crash at a chosen point/severity
    without a phone. Runs through the REAL ingest pipeline -- same
    enrichment, same scoring, same gateway call -- so the demo exercises the
    actual code path, not a canned response.
    """
    if req.channel_hint == "SMS":
        now = datetime.now(UTC)
        sms_body = encode_rrx1(
            alert_uuid=uuid.uuid4(), lat=req.lat, lon=req.lon, occurred_at=now,
            severity=req.severity.value, speed_kmh=req.speed_kmh, heading_deg=90.0,
            gps_accuracy_m=5.0, peak_g=req.peak_g, cancel_window_expired=True,
        )
        parsed = parse_rrx1(sms_body)   # round-trips through the real wire format
        return await ingest_sms(db, redis, gateway, parsed)

    payload = AlertCreate(
        alert_uuid=uuid.uuid4(),
        device_id=None,
        occurred_at=datetime.now(UTC),
        location=Location(lat=req.lat, lon=req.lon, accuracy_m=5.0),
        motion=Motion(speed_kmh=req.speed_kmh, heading_deg=90.0, peak_g=req.peak_g,
                     delta_v_kmh=req.speed_kmh * 0.6, rollover=False, still_moving=False),
        detection=Detection(p_crash=0.95, severity=req.severity, model_version="simulator"),
        window=Window(duration_s=10, outcome="EXPIRED"),
        device_context=DeviceContext(locale="en-IN"),
        is_simulated=True,   # this alert is fabricated by the demo tool itself
    )
    return await ingest_alert(db, redis, gateway, payload)


@router.post("/gateway/mode")
async def sim_gateway_mode(req: GatewayModeRequest) -> dict:
    """UX-APPFLOW.md §25: force ok/slow/timeout/reject to demonstrate the
    system degrading correctly when the (simulated) government endpoint
    misbehaves -- verified against the real gateway in app/gateways/simulated.py.
    """
    gateway_mode_state.mode = req.mode
    return {"mode": gateway_mode_state.mode.value}
