"""PRD §11.2: a faithful mock of the dispatch workflow, not a stub that
returns 200 OK. The interface is real even though the counterparty isn't.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from enum import Enum

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.gateways.base import DispatchGateway, GatewayRejected, GatewayTimeout
from app.schemas.dispatch import DispatchAck, DispatchPayload, DispatchStatus
from app.services.responders import find_nearest

log = structlog.get_logger()


class GatewayMode(str, Enum):
    """PRD §11.2 point 7: injectable failure modes, settable at runtime via
    POST /sim/gateway/mode so a demo can show the system degrading correctly
    when the government endpoint misbehaves.
    """

    OK = "ok"
    SLOW = "slow"
    TIMEOUT = "timeout"
    REJECT = "reject"


class GatewayModeState:
    """Shared mutable state, one instance per process. Deliberately NOT an
    enum/constant -- /sim/gateway/mode mutates this at runtime, in place,
    without needing to touch every place the gateway was constructed.
    """

    def __init__(self) -> None:
        self.mode: GatewayMode = GatewayMode.OK


class SimulatedPmRahatGateway(DispatchGateway):
    """v1's only implementation. The Protocol in base.py is what makes
    `Erss112Gateway(DispatchGateway)` a drop-in replacement later -- see
    PRD §11.3. This class is intentionally the only one that knows it's fake.
    """

    GATEWAY_NAME = "SIMULATED_PM_RAHAT"

    def __init__(self, session_factory: async_sessionmaker, mode_state: GatewayModeState):
        self._session_factory = session_factory
        self._mode_state = mode_state
        # In-memory ticket state machine -- sufficient for a single-process
        # demo deployment. A multi-worker deployment would move this to Redis;
        # noted as a known limitation, not silently papered over.
        self._tickets: dict[str, dict] = {}

    def _new_ticket_id(self, at: datetime) -> str:
        # Matches the PRD §11.4 worked example's format exactly:
        # "SIM-2026-0814-004417"
        suffix = f"{uuid.uuid4().int % 1_000_000:06d}"
        return f"SIM-{at.year:04d}-{at.month:02d}{at.day:02d}-{suffix}"

    async def submit(self, incident: DispatchPayload) -> DispatchAck:
        t0 = time.monotonic()
        mode = self._mode_state.mode
        log.info("gateway.submit.start", gateway=self.GATEWAY_NAME, mode=mode.value,
                 severity=incident.severity, lat=incident.location.lat, lon=incident.location.lon)

        if mode == GatewayMode.SLOW:
            await asyncio.sleep(4.0)
        elif mode == GatewayMode.TIMEOUT:
            await asyncio.sleep(0.05)
            log.warning("gateway.submit.timeout", gateway=self.GATEWAY_NAME)
            raise GatewayTimeout("SIMULATED_PM_RAHAT did not respond in time (injected mode=timeout)")
        elif mode == GatewayMode.REJECT:
            log.warning("gateway.submit.rejected", gateway=self.GATEWAY_NAME)
            raise GatewayRejected("SIMULATED_PM_RAHAT declined the incident (injected mode=reject)")

        now = datetime.now(UTC)
        ticket_id = self._new_ticket_id(now)

        # PRD §11.2 point 4: select the nearest available responder unit by
        # PostGIS distance and mark it assigned.
        async with self._session_factory() as db:
            nearest = await find_nearest(db, incident.location.lat, incident.location.lon, limit=1)
        unit = nearest[0] if nearest else None

        self._tickets[ticket_id] = {"status": "ACKNOWLEDGED", "updated_at": now}
        latency_ms = int((time.monotonic() - t0) * 1000)

        raw_response = {
            "ticket_id": ticket_id,
            "status": "ACKNOWLEDGED",
            "assigned_unit": unit.name if unit else None,
            "note": "Demonstration mode -- this dispatch is simulated.",
        }
        log.info("gateway.submit.ack", gateway=self.GATEWAY_NAME, ticket_id=ticket_id,
                 latency_ms=latency_ms, unit=unit.name if unit else None)

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
        t = self._tickets.get(ticket_id)
        if t is None:
            raise KeyError(f"unknown ticket_id {ticket_id!r}")
        return DispatchStatus(ticket_id=ticket_id, status=t["status"], updated_at=t["updated_at"])

    async def cancel(self, ticket_id: str, reason: str) -> None:
        if ticket_id in self._tickets:
            self._tickets[ticket_id]["status"] = "CANCELLED"
            self._tickets[ticket_id]["updated_at"] = datetime.now(UTC)
        log.info("gateway.cancel", gateway=self.GATEWAY_NAME, ticket_id=ticket_id, reason=reason)
