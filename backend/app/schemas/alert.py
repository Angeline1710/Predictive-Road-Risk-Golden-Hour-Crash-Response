"""Request/response schemas for POST /alerts -- PRD §10.1, transcribed field
for field from the worked example there so the wire format matches exactly.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.alert import AlertSeverity


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0)
    altitude_m: float | None = None


class Motion(BaseModel):
    speed_kmh: float = Field(ge=0)
    heading_deg: float = Field(ge=0, lt=360)
    # Peak OBSERVED (clipped) g -- a consumer accelerometer cannot measure
    # true peak past its rail in a real crash. See ml/MODELS.md §2.1 and
    # PRD §7.1: this number is a floor, not a measurement of crash severity.
    peak_g: float = Field(ge=0)
    delta_v_kmh: float | None = Field(default=None, ge=0)
    impact_direction: str | None = None   # front/rear/left/right/rollover
    rollover: bool = False
    still_moving: bool | None = None


class Detection(BaseModel):
    p_crash: float = Field(ge=0, le=1)
    severity: AlertSeverity
    model_version: str


class Window(BaseModel):
    duration_s: int = Field(ge=0)
    outcome: str   # "EXPIRED" | "CANCELLED" -- PRD UX-APPFLOW §15.5/§16


class DeviceContext(BaseModel):
    battery_pct: int | None = Field(default=None, ge=0, le=100)
    locale: str = "en-IN"
    app_version: str | None = None


class AlertCreate(BaseModel):
    """POST /alerts request body."""

    alert_uuid: UUID          # client-generated idempotency key -- PRD 10.4
    device_id: UUID | None = None
    occurred_at: datetime     # device clock, at impact
    location: Location
    motion: Motion
    detection: Detection
    window: Window
    device_context: DeviceContext = DeviceContext()
    occupant_hint: int | None = Field(default=None, ge=1, le=8)
    is_simulated: bool = False

    @field_validator("occurred_at")
    @classmethod
    def _must_be_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware (device clock, at impact)")
        return v


class RiskContext(BaseModel):
    score: float
    band: str
    top_factors: list[str]


class DispatchInfo(BaseModel):
    gateway: str
    is_simulated: bool
    ticket_id: str | None
    eta_note: str | None = None


class NearestUnit(BaseModel):
    id: int
    name: str
    kind: str
    distance_km: float


class AlertResponse(BaseModel):
    """202 Accepted body. PRD 10.4: this endpoint never returns a
    non-retryable error for a well-formed payload -- degraded enrichment
    still returns 202 with whichever fields it managed to fill in.
    """

    alert_uuid: UUID
    status: str
    segment_id: int | None = None
    landmark: str | None = None
    risk_context: RiskContext | None = None
    dispatch: DispatchInfo | None = None
    nearest_units: list[NearestUnit] = []


class AlertSummary(BaseModel):
    """GET /alerts list row -- UX-APPFLOW.md §21.2 incident rail cold-start
    (the WebSocket carries live updates after page load, but the rail needs
    an initial snapshot from somewhere). Deliberately lighter than
    AlertResponse: no dispatch payload replay, no nearest-unit recompute --
    just what the rail and map marker need to render.
    """

    alert_uuid: UUID
    status: str
    severity: str
    channel: str
    occurred_at: datetime
    received_at: datetime
    lat: float
    lon: float
    segment_id: int | None = None
    landmark: str | None = None
    risk_score: float | None = None
    risk_band: str | None = None
    is_simulated: bool
    has_trace: bool
    ticket_id: str | None = None
