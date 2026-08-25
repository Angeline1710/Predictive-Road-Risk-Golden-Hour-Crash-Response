"""PRD §10.2. /risk/point and /risk/bbox are implemented and verified here.
/risk/route, /risk/tiles, /risk/segments/{id}/history, and /risk/top are
NOT implemented yet -- tracked as a follow-up rather than stubbed out, since
a stub that returns fake data is worse than an endpoint that doesn't exist.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geography
from pydantic import BaseModel
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.ml.risk_model import RiskResult, features_from_segment, predict, predict_heatgrid
from app.models.road import RoadSegment

log = structlog.get_logger()
router = APIRouter(prefix="/risk", tags=["risk"])

MAP_MATCH_RADIUS_M = 1000   # wider than alert-ingest's 300m: a risk query can
                            # legitimately be "what's the nearest known road"


class RiskContextOut(BaseModel):
    segment_id: int
    district: str | None
    road_class: str | None
    score: float
    band: str
    top_factors: list[str]
    model_version: str
    # GeoJSON LineString [lon, lat] pairs -- UX-APPFLOW.md §21.1's risk
    # overlay draws segments stroked by band, which needs the geometry the
    # score was computed for, not just the score.
    geometry: list[list[float]]


def _coords_from_geojson(geojson_text: str) -> list[list[float]]:
    return json.loads(geojson_text)["coordinates"]


async def _nearest_segment(db: AsyncSession, lat: float, lon: float) -> tuple[RoadSegment, list[list[float]]] | None:
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    distance_m = func.ST_Distance(cast(RoadSegment.geom, Geography), cast(point, Geography))
    stmt = (
        select(RoadSegment, func.ST_AsGeoJSON(RoadSegment.geom))
        .where(distance_m <= MAP_MATCH_RADIUS_M)
        .order_by(distance_m)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    seg, geojson_text = row
    return seg, _coords_from_geojson(geojson_text)


@router.get("/point", response_model=RiskContextOut)
async def risk_point(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    at: datetime | None = Query(default=None, description="Defaults to now"),
    db: AsyncSession = Depends(get_db),
) -> RiskContextOut:
    found = await _nearest_segment(db, lat, lon)
    if found is None:
        # Honest 404, not a fabricated score -- PRD §4.7 "No data" band
        # exists in the UX spec precisely for this case.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no road segment within {MAP_MATCH_RADIUS_M}m of ({lat}, {lon}) -- "
            "the corridor ETL (MVP-PLAN.md task #11) has not populated this area yet",
        )
    seg, coords = found
    result: RiskResult = predict(features_from_segment(seg, at or datetime.now(UTC)))
    return RiskContextOut(
        segment_id=seg.segment_id, district=seg.district, road_class=seg.road_class,
        score=result.score, band=result.band, top_factors=result.top_factors,
        model_version=result.model_version, geometry=coords,
    )


@router.get("/bbox", response_model=list[RiskContextOut])
async def risk_bbox(
    minlat: float = Query(ge=-90, le=90), minlon: float = Query(ge=-180, le=180),
    maxlat: float = Query(ge=-90, le=90), maxlon: float = Query(ge=-180, le=180),
    at: datetime | None = Query(default=None),
    # Condition-simulator overrides (UX-APPFLOW.md §23) -- omit all three for
    # real-time scoring. Restricted to the exact categories risk_model_v1.txt
    # was trained on (ml/risk_model/build_panel.py); any other string would
    # silently fall through LightGBM's saved category mapping to an
    # "unknown" code rather than error, so this whitelist is load-bearing,
    # not decorative.
    weather: Literal["clear", "rain", "fog"] | None = Query(default=None),
    visibility: Literal["high", "medium", "low"] | None = Query(default=None),
    traffic_density: Literal["low", "medium", "high"] | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[RiskContextOut]:
    if minlat >= maxlat or minlon >= maxlon:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "min must be less than max on both axes")
    envelope = func.ST_MakeEnvelope(minlon, minlat, maxlon, maxlat, 4326)
    stmt = (
        select(RoadSegment, func.ST_AsGeoJSON(RoadSegment.geom))
        .where(func.ST_Intersects(RoadSegment.geom, envelope))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    at = at or datetime.now(UTC)
    out = []
    for seg, geojson_text in rows:
        result = predict(features_from_segment(
            seg, at, weather=weather, visibility=visibility, traffic_density=traffic_density,
        ))
        out.append(RiskContextOut(
            segment_id=seg.segment_id, district=seg.district, road_class=seg.road_class,
            score=result.score, band=result.band, top_factors=result.top_factors,
            model_version=result.model_version, geometry=_coords_from_geojson(geojson_text),
        ))
    return out


class HeatCellOut(BaseModel):
    dow: int    # 0=Monday ... 6=Sunday, matching datetime.weekday()
    hour: int
    score: float
    band: str
    top_factor: str | None


@router.get("/heatgrid", response_model=list[HeatCellOut])
async def risk_heatgrid(
    segment_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[HeatCellOut]:
    """UX-APPFLOW.md §23's Corridor mode heat-grid -- one real 24x7 grid
    for a single segment, scored in one batched LightGBM call
    (`predict_heatgrid`'s own docstring explains why batching, not a
    smaller grid, is the fix for what would otherwise be a slow endpoint).
    Uses `at=now` only to source non-time features (district, road_class,
    geometry-derived columns); hour and day-of-week are swept explicitly,
    not read from `at`.
    """
    seg = (await db.execute(select(RoadSegment).where(RoadSegment.segment_id == segment_id))).scalar_one_or_none()
    if seg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"segment {segment_id} not found")
    cells = predict_heatgrid(features_from_segment(seg, datetime.now(UTC)))
    return [
        HeatCellOut(dow=c.dow, hour=c.hour, score=c.score, band=c.band, top_factor=c.top_factor)
        for c in cells
    ]
