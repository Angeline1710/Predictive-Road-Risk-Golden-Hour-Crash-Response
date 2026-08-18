"""PRD §9 'Dispatch (simulated in v1)'."""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alert_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.alert_uuid"), nullable=False)
    gateway: Mapped[str] = mapped_column(Text, nullable=False)   # 'SIMULATED_PM_RAHAT' | 'ERSS112_LIVE'
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    external_ticket_id: Mapped[str | None] = mapped_column(Text)
    responder_unit_id: Mapped[int | None] = mapped_column(BigInteger)
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    requested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ResponderUnit(Base):
    __tablename__ = "responder_units"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)   # ambulance|hospital|police|trauma_centre
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    capacity: Mapped[int | None] = mapped_column(SmallInteger)
    is_seeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (Index("responder_units_geom_gix", "geom", postgresql_using="gist"),)
