"""PRD §11.3's swap point: `RRX_GATEWAY=simulated|erss112` selects the
implementation. Adding `erss112` here (once real API access exists) is the
entire integration -- no other file in the app imports a concrete gateway
class, only `app.gateways.get_gateway`.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.db import SessionLocal
from app.gateways.base import DispatchGateway
from app.gateways.simulated import GatewayModeState, SimulatedPmRahatGateway

gateway_mode_state = GatewayModeState()


@lru_cache
def get_gateway() -> DispatchGateway:
    if settings.gateway == "simulated":
        return SimulatedPmRahatGateway(SessionLocal, gateway_mode_state)
    raise NotImplementedError(
        f"RRX_GATEWAY={settings.gateway!r} has no implementation yet -- "
        "PRD 11.3: this is meant to be the only line that changes when "
        "ERSS-112 access is granted, by adding an Erss112Gateway class here."
    )
