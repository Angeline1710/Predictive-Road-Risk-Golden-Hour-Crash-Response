"""UX-APPFLOW.md §24. All aggregates below are computed live from real
tables -- no cached rollup or precomputed report, since alert/segment
counts at demo-corridor scale are small enough that a live GROUP BY can't
meaningfully drift stale between requests.

Two panels from §24's spec are NOT served here: "Detection quality" (cancel
rate per 100 drive-hours) has no real operational source -- POST /alerts'
own `window.outcome` field is accepted but never persisted anywhere
(app/services/alerts.py never reads `payload.window`), so there is no
cancel signal in this database to aggregate -- and "Risk model performance"
(PR-AUC/Brier/Precision@top-1%) is static training-time evaluation data
from ml/reports/risk_model_results.json, not something this live database
holds. Both are served as frontend constants instead (see
web/src/pages/Analytics.tsx), same posture as risk_model.py's own
BAND_THRESHOLDS being copied from that report rather than re-read live.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.alert import Alert
from app.models.device import Device
from app.models.dispatch import Dispatch, ResponderUnit
from app.models.road import RoadSegment

router = APIRouter(prefix="/analytics", tags=["analytics"])

DEVICE_ACTIVE_WINDOW_HOURS = 24   # matches app/api/devices.py's own window


class LatencyBucket(BaseModel):
    label: str
    le_s: float | None   # None = "and above" (the last, open-ended bucket)
    count: int


class LatencyStats(BaseModel):
    n: int
    p50_s: float | None
    p95_s: float | None
    p99_s: float | None
    histogram: list[LatencyBucket]


class ChannelBucket(BaseModel):
    hour: datetime
    data: int
    sms: int
    manual_sos: int


class GoldenHourStats(BaseModel):
    n: int
    within_60min_pct: float | None
    within_30min_pct: float | None
    within_15min_pct: float | None


class CoverageStats(BaseModel):
    devices_active: int
    devices_total: int
    segment_count: int
    network_km: float
    districts: list[str]
    responder_unit_count: int


class AnalyticsSummary(BaseModel):
    since_hours: int
    alert_count: int
    response_latency: LatencyStats
    channel_mix: list[ChannelBucket]
    golden_hour: GoldenHourStats
    coverage: CoverageStats


# Fixed, semantically-meaningful edges (not equal-width linear bins) --
# response latency spans sub-second acks to multi-hour stragglers, and a
# linear histogram over that range would dump everything into one bucket.
# These mirror the same 60/30/15-minute Golden-Hour breakpoints the
# response itself reports elsewhere, plus finer resolution under a minute.
_HISTOGRAM_EDGES: list[tuple[str, float | None]] = [
    ("<1s", 1), ("1-5s", 5), ("5-30s", 30), ("30s-2m", 120),
    ("2-10m", 600), ("10-60m", 3600), (">60m", None),
]


def _histogram(sorted_values: list[float]) -> list[LatencyBucket]:
    buckets = []
    lo = 0.0
    for label, edge in _HISTOGRAM_EDGES:
        hi = edge if edge is not None else float("inf")
        count = sum(1 for v in sorted_values if lo <= v < hi)
        buckets.append(LatencyBucket(label=label, le_s=edge, count=count))
        lo = hi
    return buckets


def _percentile(sorted_values: list[float], p: float) -> float:
    """Nearest-rank percentile -- fine at the alert counts a demo corridor
    produces; not worth a real interpolated implementation (or pushing this
    into Postgres via percentile_cont) for a handful of rows."""
    idx = max(0, min(len(sorted_values) - 1, int(round(p * (len(sorted_values) - 1)))))
    return sorted_values[idx]


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    since_hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummary:
    since = datetime.now(UTC) - timedelta(hours=since_hours)

    # Latest dispatch per alert -- same subquery shape as list_alerts, but
    # this one also needs acknowledged_at, which the rail doesn't.
    latest_dispatch = (
        select(Dispatch.alert_uuid, Dispatch.acknowledged_at)
        .distinct(Dispatch.alert_uuid)
        .order_by(Dispatch.alert_uuid, Dispatch.requested_at.desc())
        .subquery()
    )
    rows = (await db.execute(
        select(Alert.occurred_at, Alert.channel, latest_dispatch.c.acknowledged_at)
        .outerjoin(latest_dispatch, latest_dispatch.c.alert_uuid == Alert.alert_uuid)
        .where(Alert.received_at >= since)
    )).all()

    # response_latency / golden_hour: occurred_at -> Dispatch.acknowledged_at.
    # Real, computable timestamps -- but acknowledged_at is set synchronously
    # in-process the moment SimulatedPmRahatGateway.submit() returns (see
    # app/services/alerts.py), so this measures ingest + internal processing
    # + the simulated gateway's own (near-instant, unless /sim/gateway/mode
    # is set to "slow") response -- NOT a real PM-RAHAT/ERSS-112 field
    # acknowledgement. The frontend surfaces this caveat next to the number,
    # the same way Incident Detail's Simulation Seal discloses "no live
    # government link" rather than letting a real-looking number pass
    # unlabelled (UX-APPFLOW.md §7.5).
    latencies = sorted(
        (row.acknowledged_at - row.occurred_at).total_seconds()
        for row in rows if row.acknowledged_at is not None
    )
    response_latency = LatencyStats(
        n=len(latencies),
        p50_s=_percentile(latencies, 0.50) if latencies else None,
        p95_s=_percentile(latencies, 0.95) if latencies else None,
        p99_s=_percentile(latencies, 0.99) if latencies else None,
        histogram=_histogram(latencies),
    )
    golden_hour = GoldenHourStats(
        n=len(latencies),
        within_60min_pct=(100.0 * sum(1 for s in latencies if s <= 3600) / len(latencies)) if latencies else None,
        within_30min_pct=(100.0 * sum(1 for s in latencies if s <= 1800) / len(latencies)) if latencies else None,
        within_15min_pct=(100.0 * sum(1 for s in latencies if s <= 900) / len(latencies)) if latencies else None,
    )

    # channel_mix: DATA vs SMS vs MANUAL_SOS, bucketed by hour of ingest.
    bucket = func.date_trunc("hour", Alert.received_at)
    mix_rows = (await db.execute(
        select(bucket.label("hour"), Alert.channel, func.count())
        .where(Alert.received_at >= since)
        .group_by(bucket, Alert.channel)
        .order_by(bucket)
    )).all()
    buckets: dict[datetime, dict[str, int]] = {}
    for hour, channel, count in mix_rows:
        buckets.setdefault(hour, {"DATA": 0, "SMS": 0, "MANUAL_SOS": 0})[channel.value] = count
    channel_mix = [
        ChannelBucket(hour=hour, data=counts["DATA"], sms=counts["SMS"], manual_sos=counts["MANUAL_SOS"])
        for hour, counts in sorted(buckets.items())
    ]

    devices_since = datetime.now(UTC) - timedelta(hours=DEVICE_ACTIVE_WINDOW_HOURS)
    devices_active = (await db.execute(
        select(func.count()).select_from(Device).where(Device.last_seen_at >= devices_since)
    )).scalar_one()
    devices_total = (await db.execute(select(func.count()).select_from(Device))).scalar_one()

    segment_count = (await db.execute(select(func.count()).select_from(RoadSegment))).scalar_one()
    network_m = (await db.execute(select(func.coalesce(func.sum(RoadSegment.length_m), 0.0)))).scalar_one()
    districts = sorted(
        d for (d,) in (await db.execute(
            select(RoadSegment.district).distinct().where(RoadSegment.district.is_not(None))
        )).all()
    )
    responder_unit_count = (await db.execute(select(func.count()).select_from(ResponderUnit))).scalar_one()

    return AnalyticsSummary(
        since_hours=since_hours,
        alert_count=len(rows),
        response_latency=response_latency,
        channel_mix=channel_mix,
        golden_hour=golden_hour,
        coverage=CoverageStats(
            devices_active=devices_active, devices_total=devices_total,
            segment_count=segment_count, network_km=round(network_m / 1000.0, 2),
            districts=districts, responder_unit_count=responder_unit_count,
        ),
    )
