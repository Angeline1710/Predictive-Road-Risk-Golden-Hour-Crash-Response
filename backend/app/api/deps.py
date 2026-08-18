from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis

from app.db import get_db  # re-exported for a single import point

__all__ = ["get_db", "get_redis"]


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis
