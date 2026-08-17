"""Build the segment x hour-of-week panel that Model B trains on.

WHAT IS REAL AND WHAT IS MODELLED -- read this before quoting any metric.

REAL (from tn_road_accident_dataset_original.csv):
  * Per-district accident and fatality counts for 43 TN districts, 2021.
  * The 2.3x spread in fatal share across districts (0.152 - 0.354).
  * The vulnerable-road-user death share per district (mean 0.446).
  These set the ABSOLUTE INTENSITY and the RELATIVE SPATIAL ORDERING of the
  panel. A district that really had 1,614 accidents gets a proportionally
  larger expected count than one that had 210.

SUPPLIED PRIOR (from indian_roads_dataset.csv `risk_score` structure):
  * Condition multipliers for weather, visibility, traffic density, peak hour
    and hour-of-day. Taken from the dataset's own encoded prior, not invented.

MODELLED (this file):
  * Allocation of a district's real total across segments within it, and the
    road-geometry effects (curvature, junction density, lighting, lane count).
    Segment geometry is drawn from distributions; the effects use published
    road-safety relationships.

CONSEQUENCE: Model B's reported metrics measure whether the pipeline can
RECOVER a known risk structure from noisy Poisson counts under proper
spatio-temporal blocking. They are not evidence about Indian road physics.
The moment real iRAD segment data is available, `build_panel` is the only file
that changes -- the trainer, the CV design and the metrics stay as they are.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.common.config import DATA_PROC, SEED
from ml.risk_model.ingest import condition_multipliers, load_tn_districts

HOURS_PER_WEEK = 168
SEG_LEN_M = 500          # iRAD black-spot unit (PRD 4.7 / 7.2)
OBS_YEARS = 3            # iRAD black-spot rule is defined over 3 years

# Segments per district, scaled to the district's real road network rather than
# a flat 90. A first pass used 90 and produced 79% black-spot segments, which is
# absurd -- real black-spot prevalence is low single-digit percent. The error was
# concentrating a district's entire annual crash total onto 90 stretches of road.
# TN has roughly 2 lakh km of road; at 500 m per segment that is ~400k segments
# statewide. We model a representative sample, sized by district exposure.
SEGMENTS_TOTAL = 40_000

# The panel models the MONITORED CORRIDOR NETWORK -- national/state highways and
# urban arterials -- not TN's entire ~2 lakh km road inventory. Severe crashes
# concentrate heavily on high-order roads, so this subset carries most of the
# state's fatal crashes while being a small share of total road length. Without
# this correction the panel puts 100% of TN's crashes onto a 4% network sample
# and produces a 22% black-spot rate, roughly 10x reality.
MONITORED_CRASH_SHARE = 0.70

# Crash counts are strongly overdispersed: a minority of stretches carry a
# large share of crashes, which is exactly why black spots exist as a concept.
# A pure Poisson cannot reproduce that. A gamma frailty per segment (i.e. a
# negative-binomial) can, and it is the standard model for crash counts.
FRAILTY_SHAPE = 0.45     # smaller => more concentrated

ROAD_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary", "residential"]
ROAD_CLASS_P = [0.05, 0.14, 0.20, 0.24, 0.22, 0.15]
# Relative exposure weight -- higher-class roads carry far more vehicle-km per
# 500 m, so they accumulate more crashes at equal risk-per-km.
ROAD_EXPOSURE = {"motorway": 4.2, "trunk": 3.1, "primary": 2.2,
                 "secondary": 1.4, "tertiary": 0.9, "residential": 0.45}


def make_segments(tn: pd.DataFrame, total_segments: int = SEGMENTS_TOTAL,
                  rng: np.random.Generator | None = None) -> pd.DataFrame:
    rng = rng or np.random.default_rng(SEED)
    # Allocate segments in proportion to district accident volume, which is the
    # best available proxy for road-network size and exposure. Floor at 60 so
    # small districts are still represented.
    w = tn["total_2021"] / tn["total_2021"].sum()
    alloc = np.maximum(60, np.round(w * total_segments).astype(int))
    rows = []
    for (_, d), n in zip(tn.iterrows(), alloc):
        cls = rng.choice(ROAD_CLASSES, size=n, p=ROAD_CLASS_P)
        urban_bias = 0.75 if d["is_city_unit"] else 0.30
        for i in range(n):
            c = cls[i]
            is_urban = int(rng.random() < urban_bias)
            rows.append({
                "segment_id": f"{d['District'][:12].replace(' ', '')}_{i:04d}",
                "district": d["District"],
                "road_class": c,
                "exposure": ROAD_EXPOSURE[c],
                "length_m": SEG_LEN_M,
                "is_urban": is_urban,
                # Curvature: rural/hill segments are more sinuous.
                "curvature_deg": float(abs(rng.gamma(1.8, 9.0 if not is_urban else 5.0))),
                "gradient_pct": float(abs(rng.normal(0, 2.2))),
                "lanes": int(np.clip(rng.poisson(3 if c in ("motorway", "trunk") else 2), 1, 6)),
                "junction_count": int(rng.poisson(3.2 if is_urban else 0.9)),
                "is_lit": int(rng.random() < (0.82 if is_urban else 0.19)),
                "has_median": int(rng.random() < (0.7 if c in ("motorway", "trunk") else 0.2)),
                "speed_limit_kmh": int(rng.choice([40, 50, 60, 80, 100],
                                                  p=[.18, .26, .28, .19, .09])),
                # District-level real signal, carried onto every segment.
                "district_fatal_share": float(d["fatal_share_2021"]),
                "district_vru_share": float(d["vru_death_share"]),
                "district_heavy_share": float(d["heavy_death_share"]),
                "district_total_2021": float(d["total_2021"]),
                "district_yoy": float(d["yoy_growth"]),
            })
    return pd.DataFrame(rows)


def _geometry_log_risk(seg: pd.DataFrame) -> np.ndarray:
    """Road-geometry contribution, in log space.

    Effect directions and rough magnitudes follow the standard road-safety
    literature: sinuosity and junction density raise risk; medians and lighting
    lower it; higher speed limits raise severity risk.
    """
    z = np.zeros(len(seg))
    z += 0.011 * np.clip(seg["curvature_deg"], 0, 60)
    z += 0.030 * np.clip(seg["gradient_pct"], 0, 10)
    z += 0.085 * np.clip(seg["junction_count"], 0, 10)
    z -= 0.240 * seg["has_median"]
    z -= 0.150 * seg["is_lit"]
    z += 0.009 * (seg["speed_limit_kmh"] - 60)
    z -= 0.045 * (seg["lanes"] - 2)
    return z.to_numpy()


def build(total_segments: int = SEGMENTS_TOTAL, weeks: int = 1,
          seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tn = load_tn_districts()
    cm = condition_multipliers()
    seg = make_segments(tn, total_segments, rng)

    hours = np.arange(HOURS_PER_WEEK)
    hod = hours % 24
    dow = hours // 24
    hour_mult = np.array([cm["hour"][str(h)] for h in hod])
    weekend = (dow >= 5).astype(int)

    n_seg, n_hr = len(seg), HOURS_PER_WEEK * weeks
    print(f"panel: {n_seg} segments x {n_hr} hours = {n_seg*n_hr:,} rows")

    seg_geo = _geometry_log_risk(seg)

    # --- weather / traffic state per (district, hour) ------------------------
    # Weather is spatially correlated: it is drawn per district-hour, not per
    # segment, which is also what makes blocked CV necessary.
    dists = seg["district"].unique()
    dmap = {d: i for i, d in enumerate(dists)}
    W = rng.choice(["clear", "rain", "fog"], size=(len(dists), n_hr), p=[0.62, 0.26, 0.12])
    # Fog concentrates in the small hours; resample the daytime ones.
    night = np.isin(np.tile(hod, weeks), np.r_[0:7, 21:24])
    fogmask = (W == "fog") & ~night[None, :]
    W[fogmask] = rng.choice(["clear", "rain"], size=fogmask.sum(), p=[0.7, 0.3])

    VIS = np.where(W == "fog", "low", np.where(W == "rain", "medium", "high"))
    TR = np.empty((len(dists), n_hr), dtype=object)
    peak = np.isin(np.tile(hod, weeks), [8, 9, 10, 17, 18, 19])
    for i in range(len(dists)):
        p_hi = np.where(peak, 0.55, 0.18)
        u = rng.random(n_hr)
        TR[i] = np.where(u < p_hi, "high", np.where(u < p_hi + 0.35, "medium", "low"))

    seg_d = seg["district"].map(dmap).to_numpy()

    w_mult = np.vectorize(lambda k: cm["weather"][k])(W)
    v_mult = np.vectorize(lambda k: cm["visibility"][k])(VIS)
    t_mult = np.vectorize(lambda k: cm["traffic_density"][k])(TR)

    # --- intensity ----------------------------------------------------------
    # Real district totals set the scale. A district's whole-year accident count
    # is spread over its segments (weighted by exposure) and its 168 hours.
    dist_total = seg.groupby("district")["district_total_2021"].first()
    exposure_sum = seg.groupby("district")["exposure"].sum()
    # Severe-crash share = the district's REAL fatal share.
    fatal_share = tn.set_index("District")["fatal_share_2021"]

    per_seg_year = (seg["district"].map(dist_total) / seg["district"].map(exposure_sum)
                    * seg["exposure"]).to_numpy()
    severe_per_year = (per_seg_year * seg["district"].map(fatal_share).to_numpy()
                       * MONITORED_CRASH_SHARE)

    # Gamma frailty: unobserved segment-specific hazard (sight lines, surface,
    # encroachment, enforcement) that no feature captures. This is what makes a
    # black spot a black spot.
    frail = rng.gamma(FRAILTY_SHAPE, 1.0 / FRAILTY_SHAPE, size=len(seg))
    seg["frailty"] = frail

    # Target is a COUNT over OBS_YEARS accumulated into each hour-of-week cell.
    # A given hour-of-week recurs 52*OBS_YEARS times in the observation window.
    reps = 52.0 * OBS_YEARS
    severe_per_hourofweek = severe_per_year / (365.0 * 24.0) * reps
    severe_rate = severe_per_hourofweek * frail

    lam = (severe_rate[:, None]
           * np.exp(seg_geo)[:, None]
           * hour_mult[None, :] ** 1.0
           * w_mult[seg_d] * v_mult[seg_d] * t_mult[seg_d]
           * (1.0 + 0.12 * weekend)[None, :])
    # Wet-after-dry: first rain is disproportionately slippery.
    first_rain = (W == "rain") & (np.roll(W, 1, axis=1) == "clear")
    lam *= np.where(first_rain[seg_d], 1.25, 1.0)

    y = rng.poisson(lam)
    print(f"cells with >=1 severe crash: {int((y>0).sum()):,} / {y.size:,} "
          f"({(y>0).mean()*100:.3f}%)   total crashes {int(y.sum()):,}")

    # --- flatten ------------------------------------------------------------
    si, hi = np.meshgrid(np.arange(n_seg), np.arange(n_hr), indexing="ij")
    si, hi = si.ravel(), hi.ravel()
    # Drop the string segment id before the gather: at panel scale it alone
    # would cost hundreds of MB. The integer index is the join key.
    seg_slim = seg.drop(columns=["segment_id"])
    for c in ("district", "road_class"):
        seg_slim[c] = seg_slim[c].astype("category")
    df = seg_slim.iloc[si].reset_index(drop=True)
    df["segment_idx"] = si.astype(np.int32)
    df["hour_of_week"] = hi
    df["hour"] = np.tile(hod, weeks)[hi]
    df["dow"] = np.tile(dow, weeks)[hi]
    df["is_weekend"] = np.tile(weekend, weeks)[hi]
    df["weather"] = pd.Categorical(W[seg_d[si], hi])
    df["visibility"] = pd.Categorical(VIS[seg_d[si], hi])
    df["traffic_density"] = pd.Categorical(TR[seg_d[si], hi].astype(str))
    df["is_peak_hour"] = np.isin(df["hour"], [8, 9, 10, 17, 18, 19]).astype(int)
    df["is_night"] = np.isin(df["hour"], np.r_[0:6, 21:24]).astype(int)
    # Solar elevation proxy -- computed, no API needed (PRD 7.2).
    df["solar_elev"] = np.sin((df["hour"] - 6) / 12 * np.pi).clip(-1, 1)
    df["unlit_night"] = ((1 - df["is_lit"]) * df["is_night"]).astype(int)
    df["count"] = y.ravel().astype(int)
    df["y"] = (y.ravel() > 0).astype(int)
    df["lam_true"] = lam.ravel()

    # --- historical features, computed WITHOUT leakage ----------------------
    # A 3-year crash history is simulated independently of the label period,
    # exactly as it would be in production (iRAD history precedes today).
    # Prior 3-year window, disjoint from the label window but sharing the
    # segment's frailty -- which is exactly why history predicts the future.
    hist_lam = severe_per_year * np.exp(seg_geo) * frail * OBS_YEARS
    hist = rng.poisson(hist_lam)
    seg_hist = pd.Series(hist, index=seg.index)
    df["hist_severe_3y"] = seg_hist.iloc[si].to_numpy()
    # iRAD black-spot rule: 5+ fatal/grievous in 3 years on a 500 m stretch.
    df["is_blackspot"] = (df["hist_severe_3y"] >= 5).astype(int)

    df.to_parquet(DATA_PROC / "risk_panel.parquet", index=False)
    print(f"black spots (iRAD rule, >=5 severe in {OBS_YEARS}y): "
          f"{seg_hist.ge(5).sum()} / {n_seg} segments ({seg_hist.ge(5).mean()*100:.2f}%)")
    print(f"crash concentration: top 10% of segments hold "
          f"{seg_hist.nlargest(max(1,n_seg//10)).sum()/max(1,seg_hist.sum())*100:.1f}% of severe crashes")
    return df


if __name__ == "__main__":
    df = build()
    print(f"\nshape {df.shape}")
    print(f"positive rate {df.y.mean()*100:.3f}%")
    print("\npositive rate by weather:")
    print((df.groupby("weather")["y"].mean() * 100).round(3).to_string())
    print("\npositive rate by blackspot status:")
    print((df.groupby("is_blackspot")["y"].mean() * 100).round(3).to_string())
    print("\ntop districts by positive rate:")
    print((df.groupby("district")["y"].mean() * 100).sort_values(ascending=False)
          .head(8).round(3).to_string())
