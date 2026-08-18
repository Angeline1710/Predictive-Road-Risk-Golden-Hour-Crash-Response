"""PRD §11.3: the swap path.

Going live is a config change (RRX_GATEWAY=simulated|erss112) plus ONE new
class implementing this Protocol -- not a re-architecture. That is the single
most important thing this design buys, so the Protocol signature is kept
exactly as specified in the PRD rather than "improved" with extra parameters
that would make a future Erss112Gateway diverge from it.
"""
from __future__ import annotations

from typing import Protocol

from app.schemas.dispatch import DispatchAck, DispatchPayload, DispatchStatus


class DispatchGateway(Protocol):
    async def submit(self, incident: DispatchPayload) -> DispatchAck: ...
    async def status(self, ticket_id: str) -> DispatchStatus: ...
    async def cancel(self, ticket_id: str, reason: str) -> None: ...


class GatewayRejected(Exception):
    """Raised by submit() when the (simulated) gateway declines the incident."""


class GatewayTimeout(Exception):
    """Raised by submit() when the (simulated) gateway times out."""
