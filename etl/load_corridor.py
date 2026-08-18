"""Loads etl/output/*.parquet (produced by extract_corridor.py and
extract_responders.py) into the real Postgres/PostGIS database, using the
backend's OWN SQLAlchemy engine and models -- not a hand-rolled second copy
of the schema, so this script cannot silently drift from what app/models/
actually defines.

Destructive by design, scoped to exactly two tables: TRUNCATEs
road_segments and responder_units before loading. This is a corridor
refresh, not an incremental append -- re-running it is meant to replace the
prior extraction wholesale, not accumulate duplicates next to it. CASCADE is
used because any alerts referencing a segment being replaced are, by
definition, referencing a segment about to stop existing; scoped to these
two tables only, never to alerts/devices/dispatches.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd

# Reuses the backend's actual app.models/app.db rather than a parallel
# schema definition -- see module docstring.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import func, text  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models.dispatch import ResponderUnit  # noqa: E402
from app.models.road import RoadSegment  # noqa: E402

OUT_DIR = Path(__file__).parent / "output"
BATCH_SIZE = 500


async def load_segments(df: pd.DataFrame) -> None:
    async with SessionLocal() as db:
        await db.execute(text("TRUNCATE road_segments RESTART IDENTITY CASCADE"))
        await db.commit()

        for start in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[start:start + BATCH_SIZE]
            db.add_all([
                RoadSegment(
                    osm_way_id=None if pd.isna(r.osm_way_id) else int(r.osm_way_id),
                    geom=func.ST_GeomFromText(r.geom_wkt, 4326),
                    length_m=float(r.length_m), road_class=r.road_class,
                    lanes=None if pd.isna(r.lanes) else int(r.lanes),
                    speed_limit_kmh=None if pd.isna(r.speed_limit_kmh) else int(r.speed_limit_kmh),
                    curvature_deg=float(r.curvature_deg), gradient_pct=r.gradient_pct,
                    is_lit=None if pd.isna(r.is_lit) else bool(r.is_lit),
                    is_urban=bool(r.is_urban), junction_count=int(r.junction_count),
                    h3_r5=r.h3_r5, district=r.district, state=r.state,
                )
                for r in batch.itertuples()
            ])
            await db.commit()
            print(f"  segments {min(start + BATCH_SIZE, len(df))}/{len(df)}")


async def load_responders(df: pd.DataFrame) -> None:
    async with SessionLocal() as db:
        await db.execute(text("TRUNCATE responder_units RESTART IDENTITY"))
        await db.commit()
        db.add_all([
            ResponderUnit(
                name=r.name, kind=r.kind,
                geom=func.ST_SetSRID(func.ST_MakePoint(r.lon, r.lat), 4326),
                capacity=None if pd.isna(r.capacity) else int(r.capacity),
                is_seeded=bool(r.is_seeded),
            )
            for r in df.itertuples()
        ])
        await db.commit()
        print(f"  {len(df)} responder units loaded")


async def main() -> None:
    seg_path = OUT_DIR / "corridor_segments.parquet"
    resp_path = OUT_DIR / "corridor_responders.parquet"
    if not seg_path.exists():
        raise SystemExit(f"{seg_path} not found -- run extract_corridor.py first")

    segments = pd.read_parquet(seg_path)
    print(f"loading {len(segments)} segments ...")
    await load_segments(segments)

    if resp_path.exists():
        responders = pd.read_parquet(resp_path)
        print(f"loading {len(responders)} responder units ...")
        await load_responders(responders)
    else:
        print(f"  {resp_path} not found -- skipping responder load "
              "(run extract_responders.py first if needed)")


if __name__ == "__main__":
    asyncio.run(main())
