"""PRD §6.3.1: device auth via short-lived access + rotating refresh token."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings

REFRESH_TOKEN_TTL_DAYS = 30   # not specified numerically in the PRD; a mobile
                              # device shouldn't need to re-register monthly


def _make_token(device_id: UUID, kind: str, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    claims = {"sub": str(device_id), "type": kind, "iat": now, "exp": now + ttl}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def issue_token_pair(device_id: UUID) -> tuple[str, str, int]:
    ttl = timedelta(minutes=settings.access_token_ttl_min)
    access = _make_token(device_id, "access", ttl)
    refresh = _make_token(device_id, "refresh", timedelta(days=REFRESH_TOKEN_TTL_DAYS))
    return access, refresh, int(ttl.total_seconds())


def decode_token(token: str, expected_type: str = "access") -> UUID:
    """Raises JWTError (caught by the caller as a 401) on any invalid,
    expired, or wrong-type token.
    """
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if claims.get("type") != expected_type:
        raise JWTError(f"expected a {expected_type!r} token, got {claims.get('type')!r}")
    return UUID(claims["sub"])
