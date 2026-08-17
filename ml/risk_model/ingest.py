"""Ingest the two supplied reference datasets, and be explicit about what each
one can and cannot support.

------------------------------------------------------------------------------
A. tn_road_accident_dataset_original.csv   -- REAL, official, usable as label
------------------------------------------------------------------------------
45 Tamil Nadu districts/city-commissionerates, fatal and non-fatal accident
counts for 2020 and 2021, plus 2021 deaths broken down by striking-vehicle
class. This is genuine administrative data of the same lineage as the iRAD /
TARA pipeline that IIT Madras RBG Labs runs with TN Police and the TN Trauma
Commission.

We use it for what it actually supports: a REAL district-level crash and
fatality rate model. That is a small dataset (n=45) but the relationships in it
are real, and it anchors the absolute intensity of everything downstream. It
cannot support segment-level prediction, because it has no geometry.

------------------------------------------------------------------------------
B. indian_roads_dataset.csv   -- schema + condition prior ONLY, NOT a label set
------------------------------------------------------------------------------
20,000 geocoded incidents across 8 cities with exactly the feature schema the
PRD specifies. But profiling shows it is generated data, and two findings
decide how it may be used:

  1. `accident_severity` is STATISTICALLY INDEPENDENT of every feature.
     P(fatal) is 0.1483 under clear weather and 0.1500 under fog; 0.1486 on
     highways and 0.1540 in urban areas. Every conditional equals the marginal
     to three decimals. The severity column is random assignment. Training a
     severity classifier on it can only ever reproduce the base rate, so we
     do not use it as a target, and any published AUC on it would be noise
     dressed up as a result.

  2. `risk_score` is a near-deterministic function of
     (weather, visibility, traffic_density, is_peak_hour) -- quantised to
     multiples of 0.05 and ordered exactly as domain knowledge would predict
     (0.13 clear/high-vis/light-traffic/off-peak -> 0.83 fog/low-vis/
     heavy-traffic/peak). Predicting it would be reverse-engineering a formula,
     not learning road safety.

     But that formula is a reasonable encoding of domain priors, and it is the
     one piece of usable signal in the file. So we extract it as CONDITION
     MULTIPLIERS -- how much each weather/visibility/traffic/time state
     modulates risk -- rather than as a target.

Net effect: the spatial intensity of the panel is calibrated to real TN
administrative counts, and the conditional modulation is taken from the
supplied dataset's own prior. Neither is invented here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.common.config import INDIAN_ROADS_CSV, TN_ACCIDENTS_CSV

# Districts that are police units rather than geographic districts, plus the
# TOTAL row; excluded from the district model.
TN_DROP = {"TOTAL", "RP Chennai", "RP Thiruchirapalli"}


def load_tn_districts() -> pd.DataFrame:
    """Real TN district accident counts, 2020-2021."""
    df = pd.read_csv(TN_ACCIDENTS_CSV)
    df.columns = [c.strip() for c in df.columns]
    df = df[~df["District"].isin(TN_DROP)].copy()

    ren = {
        "2020- Fatal": "fatal_2020", "2021- Fatal": "fatal_2021",
        "2020- Non-fatal": "nonfatal_2020", "2021- Non-fatal": "nonfatal_2021",
        "Total - 2020": "total_2020", "Total - 2021": "total_2021",
        "Death by Lorries - 2021": "d_lorry", "Death by Buses-2021": "d_bus",
        "Death by Cars/Jeeps 2021": "d_car",
        "Death by Three-wheelers - 2021": "d_3w",
        "Death by Two-wheelers 2021": "d_2w", "Death by Others 2021": "d_other",
        "Total Deaths 2021": "deaths_2021",
    }
    df = df.rename(columns=ren)
    num = [c for c in ren.values()]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["total_2021", "fatal_2021"]).reset_index(drop=True)

    df["is_city_unit"] = df["District"].str.contains("City", case=False).astype(int)
    # Severity ratio: what share of accidents in this district are fatal.
    df["fatal_share_2021"] = df["fatal_2021"] / df["total_2021"].clip(lower=1)
    df["fatal_share_2020"] = df["fatal_2020"] / df["total_2020"].clip(lower=1)
    df["deaths_per_fatal"] = df["deaths_2021"] / df["fatal_2021"].clip(lower=1)
    df["yoy_growth"] = df["total_2021"] / df["total_2020"].clip(lower=1)
    # Vulnerable-road-user share: two- and three-wheeler deaths. India's
    # dominant crash-victim category and a strong marker of road character.
    dcols = ["d_lorry", "d_bus", "d_car", "d_3w", "d_2w", "d_other"]
    tot = df[dcols].sum(axis=1).clip(lower=1)
    for c in dcols:
        df[f"share_{c}"] = df[c] / tot
    df["vru_death_share"] = (df["d_2w"] + df["d_3w"]) / tot
    df["heavy_death_share"] = (df["d_lorry"] + df["d_bus"]) / tot
    return df


def condition_multipliers() -> dict:
    """Extract condition risk multipliers from indian_roads_dataset's own prior.

    Returns multipliers normalised so the population mean is 1.0, i.e. "how
    many times the average risk does this condition represent".
    """
    d = pd.read_csv(INDIAN_ROADS_CSV)
    base = d["risk_score"].mean()

    def mult(col):
        g = d.groupby(col, observed=True)["risk_score"].mean() / base
        return {str(k): float(v) for k, v in g.items()}

    out = {c: mult(c) for c in
           ["weather", "visibility", "traffic_density", "road_type", "is_peak_hour"]}

    # Hour-of-day profile, smoothed -- the raw curve is noisy at n=20k/24.
    hourly = d.groupby("hour", observed=True)["risk_score"].mean() / base
    h = hourly.reindex(range(24)).interpolate().to_numpy()
    h = np.convolve(np.r_[h[-2:], h, h[:2]], np.ones(3) / 3, mode="same")[2:-2]
    out["hour"] = {str(i): float(v) for i, v in enumerate(h)}
    out["_base_risk"] = float(base)
    return out


def severity_independence_check() -> pd.DataFrame:
    """Evidence for the claim that `accident_severity` carries no signal.

    Reported in the model card rather than asserted. If a future, real dataset
    replaces this file, re-running this is how you find out whether the target
    became usable.
    """
    d = pd.read_csv(INDIAN_ROADS_CSV)
    rows = []
    marg = (d["accident_severity"] == "fatal").mean()
    for c in ["weather", "visibility", "traffic_density", "road_type",
              "cause", "is_peak_hour", "is_weekend"]:
        g = d.groupby(c, observed=True)["accident_severity"].apply(
            lambda s: (s == "fatal").mean())
        rows.append({"feature": c, "min_p_fatal": g.min(), "max_p_fatal": g.max(),
                     "spread": g.max() - g.min(), "marginal": marg})
    return pd.DataFrame(rows).sort_values("spread", ascending=False)


def city_anchors() -> pd.DataFrame:
    """Real coordinate extents per city, used to place synthetic segments."""
    d = pd.read_csv(INDIAN_ROADS_CSV)
    g = d.groupby(["city", "state"], observed=True).agg(
        lat=("latitude", "mean"), lon=("longitude", "mean"),
        lat_sd=("latitude", "std"), lon_sd=("longitude", "std"), n=("city", "size"),
    ).reset_index()
    return g


if __name__ == "__main__":
    tn = load_tn_districts()
    print(f"TN districts: {len(tn)}")
    print(tn[["District", "total_2021", "fatal_2021", "deaths_2021",
              "fatal_share_2021", "vru_death_share"]].head(10).to_string(index=False))
    print(f"\nTN totals 2021: accidents={tn.total_2021.sum():,.0f} "
          f"fatal={tn.fatal_2021.sum():,.0f} deaths={tn.deaths_2021.sum():,.0f}")
    print(f"fatal share: mean={tn.fatal_share_2021.mean():.3f} "
          f"range {tn.fatal_share_2021.min():.3f}-{tn.fatal_share_2021.max():.3f}")
    print(f"VRU death share: mean={tn.vru_death_share.mean():.3f}")

    print("\n--- severity independence check (indian_roads_dataset) ---")
    print(severity_independence_check().to_string(index=False))

    print("\n--- condition multipliers extracted ---")
    cm = condition_multipliers()
    for k, v in cm.items():
        if k.startswith("_"):
            continue
        if k == "hour":
            hv = [round(v[str(i)], 2) for i in range(24)]
            print(f"  hour: {hv}")
        else:
            print(f"  {k}: { {a: round(b,3) for a,b in v.items()} }")
