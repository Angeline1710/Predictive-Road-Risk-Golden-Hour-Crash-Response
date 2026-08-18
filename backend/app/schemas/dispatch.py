"""The dispatch payload contract -- PRD §11.4, transcribed field for field.

This is deliberately LANGUAGE-NEUTRAL STRUCTURED DATA (PRD §11.4's own framing):
that is how the language barrier is removed. A real ERSS-112/PM RAHAT gateway
renders it in whatever language the operator reads; the simulated gateway
just echoes it back in the ack for audit/demo replay.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DispatchLocation(BaseModel):
    lat: float
    lon: float
    accuracy_m: float
    landmark: str | None = None
    district: str | None = None
    state: str | None = None


class DispatchEvidence(BaseModel):
    peak_g: float
    delta_v_kmh: float | None = None
    rollover: bool = False
    post_impact_motion: bool | None = None


class VictimHint(BaseModel):
    occupants_est: int | None = None
    blood_group: str | None = None
    known_conditions: list[str] = []


class DispatchConditions(BaseModel):
    weather: str | None = None
    visibility_m: float | None = None
    light: str | None = None
    traffic: str | None = None


class DispatchContact(BaseModel):
    msisdn_ref: str | None = None
    language: str = "en-IN"


class DispatchPayload(BaseModel):
    source_system: str = "RRX"
    incident_type: str = "ROAD_ACCIDENT"
    reported_at: datetime
    detection_method: str = "AUTOMATIC_ONDEVICE"
    confidence: float
    location: DispatchLocation
    severity: str
    evidence: DispatchEvidence
    victim_hint: VictimHint = VictimHint()
    conditions: DispatchConditions = DispatchConditions()
    contact: DispatchContact
    pm_rahat_eligible: bool = True
    # PRD §11.1: every artifact this touches says so -- dashed box in the
    # architecture diagram, SIMULATED banner in the UI, this field in the DB
    # and every API response. Never silently defaulted to False by omission.
    simulated: bool


class DispatchAck(BaseModel):
    """Return value of DispatchGateway.submit()."""

    ticket_id: str
    status: str                 # "ACKNOWLEDGED" | "REJECTED"
    gateway: str                # "SIMULATED_PM_RAHAT" | "ERSS112_LIVE"
    is_simulated: bool
    eta_note: str | None = None
    responder_unit_id: int | None = None
    responder_name: str | None = None
    responder_distance_km: float | None = None
    latency_ms: int = 0
    raw_response: dict = {}     # persisted verbatim into dispatches.response_payload


class DispatchStatus(BaseModel):
    ticket_id: str
    status: str
    updated_at: datetime
