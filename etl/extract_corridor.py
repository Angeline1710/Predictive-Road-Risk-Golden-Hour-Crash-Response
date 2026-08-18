"""PRD §12.6 `etl/`: real road geometry for the frozen demo corridor --
NH-45 through Chengalpattu district, Tamil Nadu (MVP-PLAN.md §2③).

Pulls from OpenStreetMap via the Overpass API (osmnx), NOT synthetic
geometry. This is what ml/risk_model/build_panel.py's segments were always
a stand-in for: real segments now exist to replace them.

Output is a self-contained Parquet file (not a DB write -- see load_corridor.py
for that), so extraction and loading are independently re-runnable: a flaky
Overpass query doesn't force redoing the DB load, and vice versa.
"""
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import h3
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.ops import substring

OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

# (west, south, east, north) -- osmnx 2.x's bbox order. Centred on the PRD's
# own worked example (12.91845, 80.22456, "NH-45 near Guduvancheri toll,
# Chengalpattu"), extended south toward Chengalpattu town along the NH-45/
# NH-32 alignment. ~20km x 22km: wide enough to be a real corridor, narrow
# enough that the Overpass query completes in a reasonable time -- a first
# test query over a ~5km box already took 75s.
CORRIDOR_BBOX = (80.05, 12.75, 80.28, 12.95)

# Major road classes only. An unfiltered bbox query pulls every residential
# side street in the box, which is not what "corridor" means here and would
# balloon both query time and segment count without adding signal -- the risk
# model's own segment panel (ml/risk_model/build_panel.py) was built on this
# same road-class set.
ROAD_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary"]
HIGHWAY_FILTER = f'["highway"~"^({"|".join(ROAD_CLASSES)})$"]'

TARGET_SEGMENT_M = 500.0   # iRAD black-spot unit, PRD §4.7/§7.2
H3_RESOLUTION = 5          # PRD §6.4
STATE = "Tamil Nadu"
DISTRICT = "Chengalpattu"


def _bearing_deg(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = math.radians(p1[1]), math.radians(p1[0]), math.radians(p2[1]), math.radians(p2[0])
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(y, x)) % 360


def _curvature_deg(coords: list[tuple[float, float]]) -> float:
    """Sum of absolute bearing change along the segment -- a cheap, real
    sinuosity measure (straight line = 0, a full U-turn accumulates ~180).
    """
    if len(coords) < 3:
        return 0.0
    bearings = [_bearing_deg(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    total = 0.0
    for i in range(len(bearings) - 1):
        d = abs(bearings[i + 1] - bearings[i])
        total += min(d, 360 - d)
    return round(total, 1)


def _parse_maxspeed(val) -> int | None:
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]
    try:
        return int(str(val).split()[0])
    except (ValueError, IndexError):
        return None


def _parse_lanes(val) -> int | None:
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]
    try:
        return max(1, min(8, int(val)))
    except ValueError:
        return None


def download_graph() -> nx.MultiDiGraph:
    print(f"querying Overpass for bbox {CORRIDOR_BBOX} (this can take 1-3 minutes)...")
    G = ox.graph_from_bbox(
        bbox=CORRIDOR_BBOX, network_type="drive", simplify=True,
        custom_filter=HIGHWAY_FILTER,
    )
    print(f"  {len(G.nodes)} nodes, {len(G.edges)} edges")
    return G


def split_into_segments(G: nx.MultiDiGraph) -> pd.DataFrame:
    """Re-chunk OSM ways (arbitrary length, broken at intersections) into
    ~500m pieces. An OSM edge between two junctions is very often shorter
    or much longer than the iRAD unit; this is the step that reconciles
    the two units of measurement.
    """
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    # Junction density (PRD's `junction_count`) needs real degree info,
    # computed on the ORIGINAL (pre-split) graph topology.
    junction_deg = dict(G.degree())

    # A MultiDiGraph stores every two-way street as TWO directed edges (u->v
    # and v->u), both pointing at the same physical carriageway. Verified
    # against this exact extraction: 778 of 2561 segments (30%) were exact
    # geometric duplicates before this dedup existed. `frozenset({u, v})` is
    # direction-independent, so the reverse edge is skipped once its forward
    # counterpart (or vice versa, whichever osmnx visits first) is kept.
    seen_undirected_edges: set[tuple[frozenset, int]] = set()

    rows = []
    for (u, v, k), edge in edges.iterrows():
        geom = edge.geometry
        if geom is None or geom.length == 0:
            continue

        undirected_key = (frozenset({u, v}), k)
        if undirected_key in seen_undirected_edges:
            continue
        seen_undirected_edges.add(undirected_key)

        way_id = edge.get("osmid")
        if isinstance(way_id, list):
            way_id = way_id[0]

        # Project to a local metre-accurate CRS for real distances (EPSG:4326
        # degrees are not uniform length) -- UTM zone 44N covers Tamil Nadu.
        geom_m = gpd.GeoSeries([geom], crs="EPSG:4326").to_crs("EPSG:32644").iloc[0]
        total_m = geom_m.length
        n_pieces = max(1, round(total_m / TARGET_SEGMENT_M))
        piece_len = total_m / n_pieces

        highway = edge.get("highway")
        if isinstance(highway, list):
            highway = highway[0]

        for i in range(n_pieces):
            piece_m = substring(geom_m, i * piece_len, (i + 1) * piece_len)
            if piece_m.length < 1:
                continue
            piece_deg = gpd.GeoSeries([piece_m], crs="EPSG:32644").to_crs("EPSG:4326").iloc[0]
            coords = list(piece_deg.coords)
            mid = coords[len(coords) // 2]

            # Junctions genuinely inside this piece: only the two endpoints
            # can be real intersections (mid-piece nodes were removed by
            # osmnx's `simplify=True`), and only when the FULL edge is one
            # piece -- for a split edge, only its first/last piece touches
            # an actual OSM junction node at all.
            jn = 0
            if i == 0:
                jn += max(0, junction_deg.get(u, 1) - 2)
            if i == n_pieces - 1:
                jn += max(0, junction_deg.get(v, 1) - 2)

            rows.append({
                "osm_way_id": int(way_id) if way_id is not None else None,
                "geom_wkt": piece_deg.wkt,
                "length_m": round(piece_m.length, 1),
                "road_class": highway if highway in ROAD_CLASSES else "tertiary",
                "lanes": _parse_lanes(edge.get("lanes")),
                "speed_limit_kmh": _parse_maxspeed(edge.get("maxspeed")),
                "curvature_deg": _curvature_deg(coords),
                "gradient_pct": None,   # no elevation source wired up -- see module docstring below
                "is_lit": {"yes": True, "no": False}.get(
                    edge.get("lit")[0] if isinstance(edge.get("lit"), list) else edge.get("lit")),
                "junction_count": jn,
                "h3_r5": h3.latlng_to_cell(mid[1], mid[0], H3_RESOLUTION),
                "district": DISTRICT,
                "state": STATE,
            })
    return pd.DataFrame(rows)


def main() -> pd.DataFrame:
    G = download_graph()
    df = split_into_segments(G)
    df["is_urban"] = df["road_class"].isin(["primary", "secondary", "tertiary"])   # see note below

    out_path = OUT_DIR / "corridor_segments.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n{len(df)} segments -> {out_path}")
    print(f"road class mix:\n{df.road_class.value_counts()}")
    print(f"lanes known: {df.lanes.notna().sum()}/{len(df)}  "
          f"speed limit known: {df.speed_limit_kmh.notna().sum()}/{len(df)}  "
          f"lit known: {df.is_lit.notna().sum()}/{len(df)}")
    return df


if __name__ == "__main__":
    main()

# NOTE on omitted fields, so a reader doesn't mistake a gap for an oversight:
#   gradient_pct  -- no elevation/DEM source is wired up. Left NULL rather
#                    than fabricated; a real value needs SRTM or a similar
#                    raster joined by lat/lon, which is a follow-up, not a
#                    guess dressed up as data.
#   is_urban      -- OSM has no direct per-way urban/rural tag. Approximated
#                    from road CLASS (motorway segments are almost always
#                    inter-city/rural in this corridor; primary/secondary/
#                    tertiary skew urban/peri-urban here) rather than a
#                    landuse-polygon intersection, which would need a second
#                    Overpass query and geometric join this pass didn't do.
#                    Documented as an approximation, not asserted as ground truth.
