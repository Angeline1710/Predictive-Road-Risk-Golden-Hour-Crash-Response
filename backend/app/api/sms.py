"""PRD §10.1's `/ingest/sms` webhook -- inbound SMS posted here by whatever
is receiving text messages (a real carrier gateway, or the companion-phone
receiver MVP-PLAN.md §2② proposes for the demo). Gateway-agnostic request
shape deliberately: real gateways (Twilio, MSG91, Kaleyra -- PRD §12.5) each
have their own webhook payload format, and adapting each of those is a
separate, deferred piece of work, not something to guess at three ways here.
"""
from __future__ import annotations

import hashlib
import hmac

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.config import settings
from app.gateways import get_gateway
from app.gateways.base import DispatchGateway
from app.schemas.alert import AlertResponse
from app.services.sms_ingest import ingest_sms
from app.services.sms_protocol import RRX1ParseError, parse_rrx1

log = structlog.get_logger()
router = APIRouter(tags=["sms"])


class InboundSms(BaseModel):
    body: str            # the raw RRX1 text
    from_msisdn: str | None = None
    received_at: str | None = None


def _verify_signature(raw_body: bytes, signature: str | None) -> None:
    """PRD NFR-S7. Raises 401 on a bad signature; logs and allows through
    (does not raise) when no secret is configured -- see config.py's
    sms_webhook_secret docstring for why that is the honest default here.
    """
    if not settings.sms_webhook_secret:
        log.warning("sms.auth.disabled", reason="RRX_SMS_WEBHOOK_SECRET not configured")
        return
    if not signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing X-RRX-Signature header")
    expected = hmac.new(settings.sms_webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "signature verification failed")


@router.post("/ingest/sms", response_model=AlertResponse)
async def ingest_sms_webhook(
    payload: InboundSms,
    x_rrx_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    gateway: DispatchGateway = Depends(get_gateway),
) -> AlertResponse:
    _verify_signature(payload.body.encode(), x_rrx_signature)

    try:
        parsed = parse_rrx1(payload.body)
    except RRX1ParseError as e:
        # A malformed/spoofed message is a 400, not a 202 -- this is NOT the
        # /alerts never-reject path: there is no valid alert_uuid to key a
        # durable-retry-queue entry on, so there is nothing safe to accept.
        log.warning("sms.parse.rejected", error=str(e), from_msisdn=payload.from_msisdn)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"malformed RRX1 message: {e}") from e

    return await ingest_sms(db, redis, gateway, parsed)
