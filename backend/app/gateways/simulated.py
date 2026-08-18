"""PRD §11.2: SimulatedPmRahatGateway.

Not a stub that returns 200 OK. A faithful mock of the dispatch workflow so
the INTERFACE is real even though the counterparty isn't:

  1. receives the enriched alert over the adapter contract       (submit())
  2. validates it against the dispatch-payload schema             (Pydantic, at the call site)
  3. creates an incident ticket with a realistic ID + state machine
  4. selects the nearest available responder_unit by PostGIS distance
  5. returns a synthetic acknowledgement with a plausible ETA
  6. logs the full request/response pair for audit and demo replay
  7. supports injectable failure modes (slow/timeout/reject)

PRD §11.1: every artifact this touches says so. `is_simulated=True` is
hardcoded here, not a config toggle -- there is no way to construct this
class and get a response that claims to be real.
"""
from __future__ import annotations

import asyncio
import random
import time
from datetime import UTC, datetime
from typing import Literal

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.gateways.base import DispatchGateway, GatewayRejected, GatewayTimeout
from app.schemas.dispatch import DispatchAck, DispatchPayload, DispatchStatus
from app.services.responders import find_nearest

log = structlog.get_logger(__name__)

FailureMode = Literal["ok", "slow", "timeout", "reject"]


class GatewayModeState:
    """Shared, mutable failure-mode switch -- PRD §10.3 `/sim/gateway/mode`
    flips this at runtime so a demo can show the system degrading correctly
    when the government endpoint misbehaves, without restarting the process.
    """

    def __init__(self) -> None:
        self.mode: FailureMode = "ok"


class SimulatedPmRahatGateway(DispatchGateway):
    GATEWAY_NAME = "SIMULATED_PM_RAHAT"

    def __init__(self, session_factory: async_sessionmaker, mode_state: GatewayModeState | None = None):
        # A session-factory, not a request-scoped session: the Protocol's
        # submit(incident) signature is fixed by PRD §11.3 to match a future
        # Erss112Gateway exactly, so DB access the simulation happens to need
        # (nearest-responder lookup) is self-contained here rather than
        # threaded through the interface.
        self._sessions = session_factory
        self._mode = mode_state or GatewayModeState()
        # In-memory ticket state -- PRD point 3, "realistic ID + state
        # machine". Fine for a single-process demo; a real deployment would
        # back this with the `dispatches` table, which the caller already
        # persists to independently.
        self._tickets: dict[str, str] = {}

    def _new_ticket_id(self, at: datetime) -> str:
        return f"SIM-{at:%Y-%m%d}-{random.randint(0, 999_999):06d}"

    async def submit(self, incident: DispatchPayload) -> DispatchAck:
        t0 = time.monotonic()
        mode = self._mode.mode

        log.info("gateway.submit.received", severity=incident.severity,
                 lat=incident.location.lat, lon=incident.location.lon, mode=mode)

        if mode == "timeout":
            # A real timeout would hang until the caller's own deadline; here
            # we fail fast with the same exception the caller would see, so
            # PRD 6.3.2's "external timeouts degrade, never block" path is
            # exercisable in a demo without an actual multi-second stall.
            log.warning("gateway.submit.simulated_timeout")
            raise GatewayTimeout("simulated gateway timeout")

        if mode == "slow":
            await asyncio.sleep(3.0)

        if mode == "reject":
            log.warning("gateway.submit.simulated_reject")
            raise GatewayRejected("simulated gateway rejection")

        async with self._sessions() as db:
            nearest = await find_nearest(db, incident.location.lat, incident.location.lon, limit=1)

        unit = nearest[0] if nearest else None
        ticket_id = self._new_ticket_id(datetime.now(UTC))
        self._tickets[ticket_id] = "ACKNOWLEDGED"

        latency_ms = int((time.monotonic() - t0) * 1000)
        raw_response = {
            "ticket_id": ticket_id,
            "status": "ACKNOWLEDGED",
            "assigned_unit": unit.name if unit else None,
            "note": "Demonstration mode -- this dispatch is simulated. "
                    "No real emergency service was contacted.",
        }
        log.info("gateway.submit.acknowledged", ticket_id=ticket_id,
                 unit=unit.name if unit else None, latency_ms=latency_ms)

        return DispatchAck(
            ticket_id=ticket_id,
            status="ACKNOWLEDGED",
            gateway=self.GATEWAY_NAME,
            is_simulated=True,
            eta_note="simulated",
            responder_unit_id=unit.id if unit else None,
            responder_name=unit.name if unit else None,
            responder_distance_km=unit.distance_km if unit else None,
            latency_ms=latency_ms,
            raw_response=raw_response,
        )

    async def status(self, ticket_id: str) -> DispatchStatus:
        st = self._tickets.get(ticket_id, "UNKNOWN")
        return DispatchStatus(ticket_id=ticket_id, status=st, updated_at=datetime.now(UTC))

    async def cancel(self, ticket_id: str, reason: str) -> None:
        if ticket_id in self._tickets:
            self._tickets[ticket_id] = "CANCELLED"
        log.info("gateway.cancel", ticket_id=ticket_id, reason=reason)
