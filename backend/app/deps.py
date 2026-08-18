"""FastAPI dependency providers that need app-wide singletons (the gateway's
failure-mode switch must be shared across requests so /sim/gateway/mode can
flip it and have every subsequent request see the change)."""
from __future__ import annotations

from app.config import settings
from app.db import SessionLocal
from app.gateways.base import DispatchGateway
from app.gateways.simulated import GatewayModeState, SimulatedPmRahatGateway

gateway_mode_state = GatewayModeState()

if settings.gateway == "simulated":
    _gateway: DispatchGateway = SimulatedPmRahatGateway(SessionLocal, gateway_mode_state)
else:
    # PRD 11.3: this branch is the ENTIRE change required to go live --
    # one new class, selected here by config. It does not exist yet because
    # no real gateway access exists yet (PRD 11.1).
    raise NotImplementedError(f"RRX_GATEWAY={settings.gateway!r} has no implementation yet")


def get_gateway() -> DispatchGateway:
    return _gateway
