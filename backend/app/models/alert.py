"""PRD §9 'Alerts'. This is the hot path -- ingest, dedup, dispatch."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import REAL, BigInteger, Boolean, ForeignKey, Index, LargeBinary, SmallInteger, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertChannel(str, enum.Enum):
    DATA = "DATA"
    SMS = "SMS"
    MANUAL_SOS = "MANUAL_SOS"


class AlertSeverity(str, enum.Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    ENRICHED = "ENRICHED"
    DISPATCHED = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class Alert(Base):
    __tablename__ = "alerts"

    # Client-generated; THE idempotency key (PRD 6.3.1 / 10.4). Never
    # server-generated -- that would make retry-dedup impossible.
    alert_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.device_id"))
    channel: Mapped[AlertChannel] = mapped_column(SAEnum(AlertChannel, name="alert_channel"), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus, name="alert_status"), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity, name="alert_severity"), nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    gps_accuracy_m: Mapped[float | None] = mapped_column(REAL)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    speed_kmh: Mapped[float | None] = mapped_column(REAL)
    heading_deg: Mapped[float | None] = mapped_column(REAL)
    peak_g: Mapped[float | None] = mapped_column(REAL)
    delta_v_kmh: Mapped[float | None] = mapped_column(REAL)
    impact_direction: Mapped[str | None] = mapped_column(Text)
    rollover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    still_moving: Mapped[bool | None] = mapped_column(Boolean)
    segment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("road_segments.segment_id"))
    landmark: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[dict | None] = mapped_column(JSONB)
    risk_score: Mapped[float | None] = mapped_column(REAL)
    risk_band: Mapped[str | None] = mapped_column(Text)
    model_a_version: Mapped[str | None] = mapped_column(Text)
    model_b_version: Mapped[str | None] = mapped_column(Text)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_trace: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("alerts_geom_gix", "geom", postgresql_using="gist"),
        Index("alerts_received_idx", received_at.desc()),
    )


class AlertEvent(Base):
    """Immutable audit trail -- never updated or deleted, only appended."""

    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alert_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.alert_uuid", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus, name="alert_status"), nullable=False)
    at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    actor: Mapped[str | None] = mapped_column(Text)   # 'device' | 'backend' | 'gateway-sim' | operator id
    detail: Mapped[dict | None] = mapped_column(JSONB)


class SensorTrace(Base):
    __tablename__ = "sensor_traces"

    alert_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.alert_uuid", ondelete="CASCADE"), primary_key=True
    )
    sample_hz: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)   # zstd-compressed float16
    label: Mapped[str | None] = mapped_column(Text)   # 'crash' | 'cancelled_fp' -> training feedback
