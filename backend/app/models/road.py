"""PRD §9 'Road network'."""
from __future__ import annotations

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, REAL, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    segment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    osm_way_id: Mapped[int | None] = mapped_column(BigInteger)
    geom: Mapped[str] = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False)
    length_m: Mapped[float] = mapped_column(REAL, nullable=False)   # ~500m, iRAD black-spot unit
    road_class: Mapped[str | None] = mapped_column(Text)            # motorway/trunk/primary/...
    lanes: Mapped[int | None] = mapped_column(SmallInteger)
    speed_limit_kmh: Mapped[int | None] = mapped_column(SmallInteger)
    curvature_deg: Mapped[float | None] = mapped_column(REAL)
    gradient_pct: Mapped[float | None] = mapped_column(REAL)
    is_lit: Mapped[bool | None] = mapped_column(Boolean)
    is_urban: Mapped[bool | None] = mapped_column(Boolean)
    junction_count: Mapped[int | None] = mapped_column(SmallInteger)
    h3_r5: Mapped[str] = mapped_column(Text, nullable=False)        # weather bucketing cell
    district: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("road_segments_geom_gix", "geom", postgresql_using="gist"),
        Index("road_segments_h3_idx", "h3_r5"),
    )


class HistoricalCrash(Base):
    __tablename__ = "historical_crashes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    segment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("road_segments.segment_id"))
    occurred_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    severity: Mapped[str | None] = mapped_column(Text)               # fatal/grievous/minor
    source: Mapped[str] = mapped_column(Text, nullable=False)        # 'MoRTH-2023' | 'state-open-data'
    raw: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (Index("historical_crashes_geom_gix", "geom", postgresql_using="gist"),)


class Blackspot(Base):
    __tablename__ = "blackspots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    geom: Mapped[str] = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)        # 'MoRTH-iRAD' | 'SaveLIFE-ZFC'
    designated_on: Mapped[date | None] = mapped_column()
    fatal_count: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
