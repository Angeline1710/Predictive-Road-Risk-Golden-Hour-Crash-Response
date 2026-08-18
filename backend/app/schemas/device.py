"""PRD §10.1: register device, receive device_id + token pair; heartbeat for
liveness/config pull. Discovered as a real gap while testing POST /alerts --
alerts.device_id FKs to devices, and there was previously no way to create one.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DeviceRegister(BaseModel):
    # Salted hash of ANDROID_ID -- computed on-device (PRD NFR-PR4). The
    # backend never sees a raw hardware identifier.
    device_hash: str = Field(min_length=8)
    model: str | None = None
    android_version: str | None = None
    app_version: str | None = None
    locale: str = "en-IN"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_s: int


class DeviceRegisterResponse(BaseModel):
    device_id: UUID
    tokens: TokenPair


class Heartbeat(BaseModel):
    battery_pct: int | None = Field(default=None, ge=0, le=100)
    app_version: str | None = None


class HeartbeatResponse(BaseModel):
    """PRD §10.1: 'Liveness + config pull (thresholds, model version, feature
    flags)'. Values here are what the device should use until its next
    heartbeat -- remotely tunable per PRD §7.1 without a Play Store release.
    """

    server_time: str
    stage_a_threshold_g: float = 4.0
    stage_a_min_speed_kmh: float = 20.0
    cancel_window_s: int = 10
    model_a_version: str = "crash_fusion_v1"
    model_b_version: str = "risk_model_v1"
