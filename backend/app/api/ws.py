"""PRD §10.3: `WS /ws/events` -- live stream of alert.created,
alert.status_changed, risk.updated. Redis Pub/Sub -> WebSocket fan-out
(PRD §6.3.2 step 7), so any number of dashboard tabs/replicas can subscribe
without the backend tracking per-client alert state.
"""
from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.services.events import EVENTS_CHANNEL

log = structlog.get_logger()
router = APIRouter(tags=["events"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    redis: Redis = websocket.app.state.redis
    pubsub = redis.pubsub()
    await pubsub.subscribe(EVENTS_CHANNEL)

    async def forward() -> None:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    async def watch_disconnect() -> None:
        # starlette's WebSocket has no native "wait for close" primitive
        # other than reading -- receive() raises WebSocketDisconnect the
        # moment the client goes away, which is what actually ends this task.
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass

    forward_task = asyncio.create_task(forward())
    disconnect_task = asyncio.create_task(watch_disconnect())
    try:
        done, pending = await asyncio.wait(
            {forward_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
    finally:
        await pubsub.unsubscribe(EVENTS_CHANNEL)
        await pubsub.aclose()
        log.info("ws.events.disconnected")
