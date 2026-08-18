from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.device import Device
from app.schemas.device import (
    DeviceRegister,
    DeviceRegisterResponse,
    Heartbeat,
    HeartbeatResponse,
    TokenPair,
)
from app.services.auth import decode_token, issue_token_pair

router = APIRouter(tags=["devices"])

ACTIVE_WINDOW_HOURS = 24


class DeviceCount(BaseModel):
    active: int
    active_window_hours: int = ACTIVE_WINDOW_HOURS
    total: int


@router.get("/devices/count", response_model=DeviceCount)
async def count_devices(db: AsyncSession = Depends(get_db)) -> DeviceCount:
    """UX-APPFLOW.md §7.7's honesty bar shows a live device count -- this
    makes it a real number (devices heartbeated in the active window) rather
    than something the dashboard invents.
    """
    since = datetime.now(UTC) - timedelta(hours=ACTIVE_WINDOW_HOURS)
    active = (
        await db.execute(select(func.count()).select_from(Device).where(Device.last_seen_at >= since))
    ).scalar_one()
    total = (await db.execute(select(func.count()).select_from(Device))).scalar_one()
    return DeviceCount(active=active, total=total)


async def get_current_device_id(
    authorization: str = Header(..., description="Bearer <access_token>"),
) -> UUID:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "expected 'Bearer <token>'")
    try:
        return decode_token(authorization.removeprefix("Bearer ").strip(), expected_type="access")
    except (JWTError, ValueError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired access token") from e


@router.post("/devices/register", response_model=DeviceRegisterResponse)
async def register_device(
    payload: DeviceRegister, db: AsyncSession = Depends(get_db)
) -> DeviceRegisterResponse:
    """Idempotent on `device_hash`: a reinstall or a retried registration
    reuses the existing device_id rather than creating a duplicate row (which
    would silently orphan the old row's alert/contact history).
    """
    existing = (
        await db.execute(select(Device).where(Device.device_hash == payload.device_hash))
    ).scalar_one_or_none()

    if existing is not None:
        existing.model = payload.model or existing.model
        existing.android_version = payload.android_version or existing.android_version
        existing.app_version = payload.app_version or existing.app_version
        existing.locale = payload.locale
        existing.last_seen_at = datetime.now(UTC)
        device_id = existing.device_id
    else:
        device_id = uuid4()
        db.add(Device(
            device_id=device_id, device_hash=payload.device_hash, model=payload.model,
            android_version=payload.android_version, app_version=payload.app_version,
            locale=payload.locale, last_seen_at=datetime.now(UTC),
        ))
    await db.commit()

    access, refresh, ttl = issue_token_pair(device_id)
    return DeviceRegisterResponse(
        device_id=device_id,
        tokens=TokenPair(access_token=access, refresh_token=refresh, expires_in_s=ttl),
    )


@router.post("/devices/{device_id}/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    device_id: UUID,
    payload: Heartbeat,
    db: AsyncSession = Depends(get_db),
    authed_device_id: UUID = Depends(get_current_device_id),
) -> HeartbeatResponse:
    if authed_device_id != device_id:
        # A device's access token only ever authorises heartbeats for ITSELF.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "token does not match device_id")

    row = (await db.execute(select(Device).where(Device.device_id == device_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
    row.last_seen_at = datetime.now(UTC)
    if payload.app_version:
        row.app_version = payload.app_version
    await db.commit()

    return HeartbeatResponse(server_time=datetime.now(UTC).isoformat())
