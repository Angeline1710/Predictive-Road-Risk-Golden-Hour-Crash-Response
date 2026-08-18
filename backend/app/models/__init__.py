"""Import every model module so `Base.metadata` is complete for Alembic
autogenerate and for `create_all` in tests -- a model defined but never
imported here is invisible to both.
"""
from app.models.alert import Alert, AlertChannel, AlertEvent, AlertSeverity, AlertStatus, SensorTrace
from app.models.base import Base
from app.models.device import Device, EmergencyContact
from app.models.dispatch import Dispatch, ResponderUnit
from app.models.risk import RiskBaseline, RiskEvaluation, TrafficObservation, WeatherObservation
from app.models.road import Blackspot, HistoricalCrash, RoadSegment

__all__ = [
    "Base",
    "Device",
    "EmergencyContact",
    "RoadSegment",
    "HistoricalCrash",
    "Blackspot",
    "Alert",
    "AlertChannel",
    "AlertSeverity",
    "AlertStatus",
    "AlertEvent",
    "SensorTrace",
    "Dispatch",
    "ResponderUnit",
    "RiskEvaluation",
    "RiskBaseline",
    "WeatherObservation",
    "TrafficObservation",
]
