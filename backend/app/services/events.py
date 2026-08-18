"""PRD §6.3.2 step 7 / §10.3: broadcast alert lifecycle events over Redis
Pub/Sub, fanned out to dashboard clients by app/api/ws.py's /ws/events.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis

log = structlog.get_logger()

EVENTS_CHANNEL = "rrx:events"


async def publish_event(redis: Redis, event_type: str, data: dict) -> None:
    """Never raises -- a broadcast failure must not affect the alert
    pipeline that triggered it (same degrade-safe posture as enrichment).
    """
    try:
        message = json.dumps({
            "type": event_type,
            "at": datetime.now(UTC).isoformat(),
            "data": data,
        }, default=str)
        await redis.publish(EVENTS_CHANNEL, message)
    except Exception as e:  # noqa: BLE001
        log.warning("events.publish.failed", event_type=event_type, error=str(e))
