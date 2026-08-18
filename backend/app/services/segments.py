"""Map-matching -- PRD §6.3.2 step 3: "map-match the coordinate to the
nearest road segment (PostGIS ST_ClosestPoint over the segment index)".
"""
from __future__ import annotations

from dataclasses import dataclass

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk import RiskBaseline
from app.models.road import RoadSegment


@dataclass
class MatchedSegment:
    segment_id: int
    district: str | None
    state: str | None
    road_class: str | None
    distance_m: float


async def match_point(db: AsyncSession, lat: float, lon: float,
                      max_distance_m: float = 200.0) -> MatchedSegment | None:
    """Nearest segment within `max_distance_m`, or None.

    The distance cap matters: an alert far from every known segment (outside
    the ETL'd corridor, or before road_segments is seeded at all) must
    map-match to NOTHING rather than to whatever happens to be geometrically
    closest a hundred kilometres away. Returning None here is what lets the
    caller degrade gracefully (PRD 10.4) instead of attaching a nonsense
    landmark to the alert.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    distance_m = func.ST_Distance(cast(RoadSegment.geom, Geography), cast(point, Geography))
    stmt = (
        select(RoadSegment, distance_m.label("distance_m"))
        .order_by(distance_m)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    seg, dist = row
    if dist > max_distance_m:
        return None
    return MatchedSegment(
        segment_id=seg.segment_id, district=seg.district, state=seg.state,
        road_class=seg.road_class, distance_m=round(dist, 1),
    )


RISK_BAND_ORDER = ["Low", "Moderate", "High", "Severe"]


async def current_risk(db: AsyncSession, segment_id: int, hour_bucket: int) -> tuple[float, str] | None:
    """Baseline risk for this segment at this hour-of-week, if precomputed.

    Reads `risk_baseline` (PRD §6.4's nightly precompute), not live Model B
    inference -- that requires the feature-vector builder + booster-serving
    endpoint, which is separate, not-yet-built work (MVP-PLAN §3.1). Returns
    None when nothing has been precomputed yet, which the caller must treat
    as "no risk context available" rather than "risk is zero".
    """
    row = await db.get(RiskBaseline, {"segment_id": segment_id, "hour_bucket": hour_bucket})
    if row is None:
        return None
    return row.base_score, _band_for_score(row.base_score)


def _band_for_score(score: float) -> str:
    # Placeholder quantile thresholds until the real banding (fit on the
    # served network's live score distribution, per PRD §7.2) is wired up.
    if score < 0.25:
        return "Low"
    if score < 0.55:
        return "Moderate"
    if score < 0.8:
        return "High"
    return "Severe"
