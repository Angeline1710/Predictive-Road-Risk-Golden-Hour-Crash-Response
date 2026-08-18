"""Nearest-responder lookup -- PRD §12.1's "single PostGIS ST_DWithin query"
for the whole nearest-responder feature. Cast to geography so distances come
back in real metres rather than degrees.
"""
from __future__ import annotations

from dataclasses import dataclass

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dispatch import ResponderUnit


@dataclass
class NearestResponder:
    id: int
    name: str
    kind: str
    distance_km: float


async def find_nearest(
    db: AsyncSession, lat: float, lon: float, limit: int = 3
) -> list[NearestResponder]:
    """Cast both sides to `geography` so ST_Distance returns metres on a
    sphere rather than degrees on the raw SRID 4326 plane -- the latter is
    fast but wrong by a variable, latitude-dependent factor.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    distance_m = func.ST_Distance(cast(ResponderUnit.geom, Geography), cast(point, Geography))
    stmt = (
        select(ResponderUnit, distance_m.label("distance_m"))
        .order_by(distance_m)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        NearestResponder(id=u.id, name=u.name, kind=u.kind, distance_km=round(d / 1000.0, 1))
        for u, d in rows
    ]
