"""Model B serving. Loads the exact artifact ml/risk_model/train.py produced
-- ml/artifacts/risk_model_v1.txt -- and nothing else. See ml/MODELS.md
before trusting any score this returns: the model is trained on a synthetic
segment panel anchored to real TN district totals (real spatial intensity,
modelled segment geometry), not real per-segment history.

CATEGORICAL SAFETY: a LightGBM Booster saved via save_model() persists its
training-time `pandas_categorical` -- the exact category-to-code mapping
used to fit the model. Passing a pandas DataFrame with `category` dtype
columns to `.predict()` re-applies THAT mapping automatically, regardless of
what category values happen to be present in the query row. This is the only
safe way to serve a LightGBM model with categorical features: reconstructing
category codes by hand (e.g. sorting unique values seen at request time)
would silently diverge from training and corrupt every prediction without
raising an error. Verified empirically before writing this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

# Bundled into the backend's own tree (app/ml/models/) rather than referenced
# from the top-level ml/artifacts/ this repo also has: that directory is
# OUTSIDE the Docker build context (docker-compose.yml builds from backend/),
# so the backend ships its own deliberate, versioned copy of the artifact it
# depends on instead of reaching across a path the container can't see.
MODEL_PATH = Path(__file__).parent / "models" / "risk_model_v1.txt"
MODEL_VERSION = "risk_model_v1"

# From ml/reports/risk_model_results.json's band_thresholds -- the quantile
# cut points of the trained model's own score distribution (PRD §7.2:
# "4 bands via quantiles of the coverage-area distribution"). Hardcoded
# rather than re-read from the results JSON at import time so serving
# doesn't depend on that report file surviving in every deployment; the
# values are copied verbatim and the source is named for anyone checking.
BAND_THRESHOLDS = {"Low": 0.003256608308887652, "Moderate": 0.013658109062029763,
                   "High": 0.05329646024360551}

# Driver-facing phrasing for the raw feature names -- PRD FR-4.6: "the
# warning SHALL state the top contributing reason", not a bare feature name.
FEATURE_LABELS = {
    "hist_severe_3y": "crash history here", "weather": "weather", "visibility": "low visibility",
    "traffic_density": "heavy traffic", "curvature_deg": "sharp curve", "gradient_pct": "steep grade",
    "junction_count": "junctions nearby", "is_lit": "lighting", "has_median": "no median",
    "speed_limit_kmh": "speed limit", "is_night": "night", "unlit_night": "unlit at night",
    "is_peak_hour": "peak-hour traffic", "is_blackspot": "known black spot",
    "district_fatal_share": "district crash severity", "solar_elev": "low light",
    "is_urban": "urban road", "lanes": "lane count", "road_class": "road type",
    "district": "this district", "hour": "time of day", "dow": "day of week",
    "is_weekend": "weekend", "exposure": "traffic volume", "hour_of_week": "time of week",
    "district_vru_share": "two-wheeler risk", "district_heavy_share": "heavy-vehicle risk",
    "district_total_2021": "district crash volume", "district_yoy": "rising crash trend",
}


@dataclass
class RiskFeatures:
    district: str
    road_class: str
    exposure: float
    is_urban: bool
    curvature_deg: float
    gradient_pct: float
    lanes: int
    junction_count: int
    is_lit: bool
    has_median: bool
    speed_limit_kmh: int
    district_fatal_share: float
    district_vru_share: float
    district_heavy_share: float
    district_total_2021: float
    district_yoy: float
    at: datetime
    weather: str = "clear"          # PRD §6.4 fallback prior when live feed unavailable
    visibility: str = "high"
    traffic_density: str = "medium"
    hist_severe_3y: int = 0
    is_blackspot: bool = False


@dataclass
class RiskResult:
    score: float
    band: str
    top_factors: list[str]
    model_version: str = MODEL_VERSION


@lru_cache
def _booster() -> lgb.Booster:
    return lgb.Booster(model_file=str(MODEL_PATH))


def _row(f: RiskFeatures) -> pd.DataFrame:
    hod, dow = f.at.hour, f.at.weekday()
    row = {
        "district": f.district, "road_class": f.road_class, "exposure": f.exposure,
        "is_urban": int(f.is_urban), "curvature_deg": f.curvature_deg,
        "gradient_pct": f.gradient_pct, "lanes": f.lanes, "junction_count": f.junction_count,
        "is_lit": int(f.is_lit), "has_median": int(f.has_median),
        "speed_limit_kmh": f.speed_limit_kmh, "district_fatal_share": f.district_fatal_share,
        "district_vru_share": f.district_vru_share, "district_heavy_share": f.district_heavy_share,
        "district_total_2021": f.district_total_2021, "district_yoy": f.district_yoy,
        "hour_of_week": dow * 24 + hod, "hour": hod, "dow": dow,
        "is_weekend": int(dow >= 5), "weather": f.weather, "visibility": f.visibility,
        "traffic_density": f.traffic_density,
        "is_peak_hour": int(hod in (8, 9, 10, 17, 18, 19)),
        "is_night": int(hod in list(range(0, 6)) + list(range(21, 24))),
        "solar_elev": float(np.clip(np.sin((hod - 6) / 12 * np.pi), -1, 1)),
        "unlit_night": int((not f.is_lit) and hod in list(range(0, 6)) + list(range(21, 24))),
        "hist_severe_3y": f.hist_severe_3y, "is_blackspot": int(f.is_blackspot),
    }
    b = _booster()
    df = pd.DataFrame([row])[b.feature_name()]
    for c in ("district", "road_class", "weather", "visibility", "traffic_density"):
        df[c] = df[c].astype("category")
    return df


def features_from_segment(segment, at: datetime) -> RiskFeatures:
    """Shared by app/api/risk.py (viewport/point queries) and
    app/services/alerts.py (scoring a just-received alert's matched
    segment) so the two call sites cannot drift into different feature
    construction for the same model. `segment` is an
    app.models.road.RoadSegment; typed loosely here to avoid a
    models<->ml import cycle.

    District-level fields are Chengalpattu's REAL 2021 figures from
    `tn_road_accident_dataset_original.csv` (via ml/risk_model/ingest.py,
    values copied here rather than imported live so the backend doesn't
    depend on the ml/ package or its CSV path at request time): 1,614 total
    accidents, 0.280 fatal share, 0.326 vulnerable-road-user death share,
    0.250 heavy-vehicle death share, 1.197 YoY growth (ml/MODELS.md §1.2).
    Every corridor segment currently carries district="Chengalpattu" (the
    whole extraction is one district -- MVP-PLAN.md §2③), so a single
    constant is accurate here, not an approximation; it stops being exactly
    right only if a future extraction spans multiple districts, at which
    point this needs a real per-district lookup instead of a constant.
    """
    return RiskFeatures(
        district=segment.district or "Chengalpattu",   # PRD demo corridor, MVP-PLAN.md §2
        road_class=segment.road_class or "primary",
        exposure=2.2, is_urban=bool(segment.is_urban), curvature_deg=segment.curvature_deg or 0.0,
        gradient_pct=segment.gradient_pct or 0.0, lanes=segment.lanes or 2,
        junction_count=segment.junction_count or 0, is_lit=bool(segment.is_lit),
        has_median=False, speed_limit_kmh=segment.speed_limit_kmh or 60,
        district_fatal_share=0.280, district_vru_share=0.326, district_heavy_share=0.250,
        district_total_2021=1614.0, district_yoy=1.197, at=at,
    )


def band_for(score: float) -> str:
    if score < BAND_THRESHOLDS["Low"]:
        return "Low"
    if score < BAND_THRESHOLDS["Moderate"]:
        return "Moderate"
    if score < BAND_THRESHOLDS["High"]:
        return "High"
    return "Severe"


def predict(f: RiskFeatures, n_factors: int = 3) -> RiskResult:
    b = _booster()
    df = _row(f)
    score = float(b.predict(df)[0])

    # Native pred_contrib=True: LightGBM's own SHAP-consistent per-feature
    # contribution, computed for THIS row -- not a cached global importance
    # ranking. Zero extra dependency (no `shap` package needed in the API).
    #
    # Ranked by ABSOLUTE contribution, sign included -- not filtered to only
    # risk-increasing factors. UX-APPFLOW.md §7.2 specifies the dashboard's
    # Segment Ribbon popover always shows "SHAP top-3 factors" for analyst
    # use, which means explaining a LOW score too (e.g. "median present"
    # pulling risk down). Sign-filtering belongs to the driver-facing warning
    # UI (only surfaced for High/Severe bands per UX §14), which is a
    # DIFFERENT, narrower consumer of this same data -- that filtering
    # decision belongs in that client, not baked into the API response.
    contrib = b.predict(df, pred_contrib=True)[0][:-1]   # drop the bias term
    ranked = sorted(zip(b.feature_name(), contrib), key=lambda x: -abs(x[1]))
    top = [FEATURE_LABELS.get(name, name) for name, _ in ranked[:n_factors]]

    return RiskResult(score=round(score, 4), band=band_for(score), top_factors=top)
