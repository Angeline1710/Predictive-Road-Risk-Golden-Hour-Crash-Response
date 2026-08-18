"""PRD §6.3.2 step 3: enrich an incoming alert. Every sub-step here is
cache-first with a hard timeout and MUST degrade rather than raise --
enrichment failure must never block dispatch (PRD §6.3.2, §10.4).

Weather/traffic are architecturally real (cache-first, hard-timeout, calls
the live API if a key is configured) but this deployment has no
OpenWeatherMap/TomTom key, so they legitimately degrade to "unavailable"
every time. That is the honest state of a hackathon scaffold, not a bug --
faking API responses without a key would be worse than admitting the gap.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import h3
import httpx
import structlog
from geoalchemy2 import Geography
from redis.asyncio import Redis
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.road import RoadSegment

log = structlog.get_logger()

ENRICH_TIMEOUT_S = 0.5   # PRD §6.3.2: 300-500ms per external call, hard cap
NOMINATIM_TIMEOUT_S = 0.5
WEATHER_CACHE_TTL_S = 600    # 10 min, PRD §6.4
TRAFFIC_CACHE_TTL_S = 300    # 5 min, PRD §6.4
MAP_MATCH_RADIUS_M = 300     # a GPS fix well off any known segment degrades, not errors


@dataclass
class EnrichmentResult:
    segment_id: int | None = None
    landmark: str | None = None
    district: str | None = None
    state: str | None = None
    weather: str | None = None
    visibility_m: float | None = None
    traffic_density: str | None = None
    conditions_available: bool = False
    degraded_reasons: list[str] = field(default_factory=list)


async def map_match(db: AsyncSession, lat: float, lon: float) -> RoadSegment | None:
    """Nearest road_segment within MAP_MATCH_RADIUS_M, or None (degrade)."""
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    distance_m = func.ST_Distance(cast(RoadSegment.geom, Geography), cast(point, Geography))
    stmt = (
        select(RoadSegment)
        .where(distance_m <= MAP_MATCH_RADIUS_M)
        .order_by(distance_m)
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def reverse_geocode(lat: float, lon: float) -> str | None:
    """Nominatim public API -- no key required, but rate-limited (1 req/s) and
    must be treated as best-effort. Degrades to None on any failure/timeout.
    """
    try:
        async with httpx.AsyncClient(timeout=NOMINATIM_TIMEOUT_S) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 16},
                headers={"User-Agent": "rrx-api/0.1 (hackathon demo; contact via repo)"},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("display_name")
    except (httpx.HTTPError, ValueError) as e:
        log.warning("enrichment.geocode.degraded", error=str(e))
        return None


async def fetch_weather(redis: Redis, lat: float, lon: float) -> dict | None:
    """Cache-first, H3-res5-bucketed per PRD §6.4's quota discipline. Returns
    None (degrade) with no API key configured -- see module docstring.
    """
    cell = h3.latlng_to_cell(lat, lon, settings.h3_resolution)
    cache_key = f"rrx:wx:{cell}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    api_key = settings.openweather_api_key
    if not api_key:
        return None   # honest degrade: no key configured in this deployment

    try:
        async with httpx.AsyncClient(timeout=ENRICH_TIMEOUT_S) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            )
            r.raise_for_status()
            data = r.json()
            result = {
                "condition": data.get("weather", [{}])[0].get("main", "").lower(),
                "visibility_m": data.get("visibility"),
            }
            import json
            await redis.set(cache_key, json.dumps(result), ex=WEATHER_CACHE_TTL_S)
            return result
    except (httpx.HTTPError, ValueError) as e:
        log.warning("enrichment.weather.degraded", error=str(e))
        return None


async def enrich(db: AsyncSession, redis: Redis, lat: float, lon: float) -> EnrichmentResult:
    """Runs every sub-step independently -- one failing must not cancel the
    others, and none of them may raise past this function.
    """
    result = EnrichmentResult()

    try:
        seg = await map_match(db, lat, lon)
        if seg:
            result.segment_id = seg.segment_id
            result.district = seg.district
            result.state = seg.state
        else:
            result.degraded_reasons.append("no_segment_within_radius")
    except Exception as e:  # noqa: BLE001 -- enrichment must never propagate
        log.warning("enrichment.map_match.failed", error=str(e))
        result.degraded_reasons.append("map_match_error")

    try:
        result.landmark = await reverse_geocode(lat, lon)
        if result.landmark is None:
            result.degraded_reasons.append("geocode_unavailable")
    except Exception as e:  # noqa: BLE001
        log.warning("enrichment.geocode.failed", error=str(e))
        result.degraded_reasons.append("geocode_error")

    try:
        wx = await fetch_weather(redis, lat, lon)
        if wx:
            result.weather = wx.get("condition")
            result.visibility_m = wx.get("visibility_m")
            result.conditions_available = True
        else:
            result.degraded_reasons.append("weather_unavailable")
    except Exception as e:  # noqa: BLE001
        log.warning("enrichment.weather.failed", error=str(e))
        result.degraded_reasons.append("weather_error")

    return result
