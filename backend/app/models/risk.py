"""PRD §9 'Risk'. Serves Model B (LightGBM) and the historical feed cache."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, REAL, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index

from app.models.base import Base


class RiskEvaluation(Base):
    __tablename__ = "risk_evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("road_segments.segment_id"), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    hour_bucket: Mapped[int] = mapped_column(SmallInteger, nullable=False)   # 0..167, hour-of-week
    risk_score: Mapped[float] = mapped_column(REAL, nullable=False)
    risk_band: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    top_factors: Mapped[dict | None] = mapped_column(JSONB)   # SHAP top-3
    model_version: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("risk_eval_seg_time_idx", "segment_id", evaluated_at.desc()),)


class RiskBaseline(Base):
    """Nightly precompute: segment x hour-of-week (PRD 6.4)."""

    __tablename__ = "risk_baseline"

    segment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("road_segments.segment_id"), primary_key=True
    )
    hour_bucket: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    base_score: Mapped[float] = mapped_column(REAL, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    h3_r5: Mapped[str] = mapped_column(Text, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)   # 'OWM' | 'IMD'
    temp_c: Mapped[float | None] = mapped_column(REAL)
    precip_mm_h: Mapped[float | None] = mapped_column(REAL)
    visibility_m: Mapped[int | None] = mapped_column(REAL)
    wind_kmh: Mapped[float | None] = mapped_column(REAL)
    humidity_pct: Mapped[float | None] = mapped_column(REAL)
    condition_code: Mapped[str | None] = mapped_column(Text)


class TrafficObservation(Base):
    __tablename__ = "traffic_observations"

    segment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("road_segments.segment_id"), primary_key=True
    )
    observed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    current_kmh: Mapped[float | None] = mapped_column(REAL)
    freeflow_kmh: Mapped[float | None] = mapped_column(REAL)
    confidence: Mapped[float | None] = mapped_column(REAL)
