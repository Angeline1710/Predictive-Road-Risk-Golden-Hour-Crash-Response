"""PRD §12.1: 'Seed responder_units from public hospital/ambulance location
data'. OSM's `amenity=hospital`/`amenity=clinic` points ARE public location
data for real, named facilities -- not fabricated placeholders. Coverage is
whatever's been mapped in OSM for the corridor, which is real but partial;
documented, not hidden.

SCOPE: hospitals/clinics only. OSM also tags `emergency=ambulance_station`
separately, which this pass does not query -- the PRD names both "hospital"
and "ambulance" location data, and only the first is covered here. A
follow-up, not a decision that ambulances don't matter.
"""
from __future__ import annotations

from pathlib import Path

import osmnx as ox
import pandas as pd

from etl.extract_corridor import CORRIDOR_BBOX

OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

TAGS = {"amenity": ["hospital", "clinic"]}
KIND_MAP = {"hospital": "hospital", "clinic": "hospital"}   # PRD kind enum has
                                                            # no separate "clinic"


def main() -> pd.DataFrame:
    print(f"querying OSM for hospitals/clinics in bbox {CORRIDOR_BBOX} ...")
    # Same (west, south, east, north) order as CORRIDOR_BBOX itself -- no
    # reordering needed, unlike the graph_from_bbox/features_from_bbox
    # argument-order mismatch this module almost repeated (verified both
    # signatures directly against osmnx 2.1.1 rather than assumed).
    gdf = ox.features_from_bbox(bbox=CORRIDOR_BBOX, tags=TAGS)
    print(f"  {len(gdf)} raw features")

    rows = []
    for _, r in gdf.iterrows():
        geom = r.geometry
        if geom is None:
            continue
        # Polygon buildings -> centroid; points pass through as-is.
        pt = geom.centroid if geom.geom_type != "Point" else geom
        name = r.get("name")
        if not name or not isinstance(name, str):
            continue   # unnamed facility -- not enough to show a driver
        rows.append({
            "name": name,
            "kind": KIND_MAP.get(r.get("amenity"), "hospital"),
            "lat": pt.y, "lon": pt.x,
            "capacity": None,   # OSM has no reliable bed-count tag
            "is_seeded": True,
        })

    df = pd.DataFrame(rows).drop_duplicates(subset=["name", "lat", "lon"])
    out_path = OUT_DIR / "corridor_responders.parquet"
    df.to_parquet(out_path, index=False)
    print(f"{len(df)} named facilities -> {out_path}")
    return df


if __name__ == "__main__":
    main()
