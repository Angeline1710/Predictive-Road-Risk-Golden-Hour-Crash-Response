"""SHAP explanations for Model B.

This is not a nice-to-have. The PRD (FR-4.6, UX 13) requires the driver-facing
warning to state a REASON -- "sharp curve, heavy rain, night" -- not a number.
A driver ignores "risk 0.84" and slows down for a cause they can see out of the
windscreen. It is also what makes the model auditable to a government
stakeholder who has to justify why a stretch was flagged.

Two outputs:
  top_factors()   per-row top-k contributors, phrased in plain language, which
                  is what the API returns alongside the score.
  global_shap()   dataset-level mean |SHAP|, for the model card.
"""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd

from ml.common.config import ARTIFACTS, REPORTS
from ml.risk_model.train import CAT, TARGET_BIN, TARGET_COUNT, load_panel

# Feature -> driver-facing phrase. Sign-aware: the same feature reads
# differently depending on which way it pushed the score.
PHRASE = {
    "curvature_deg": ("sharp curve", "gentle alignment"),
    "gradient_pct": ("steep gradient", "level road"),
    "junction_count": ("many junctions", "few junctions"),
    "has_median": ("no median divider", "divided carriageway"),
    "is_lit": ("unlit stretch", "street lighting"),
    "unlit_night": ("unlit at night", "lit or daytime"),
    "speed_limit_kmh": ("high speed limit", "low speed limit"),
    "lanes": ("narrow carriageway", "wide carriageway"),
    "weather": ("adverse weather", "clear weather"),
    "visibility": ("poor visibility", "good visibility"),
    "traffic_density": ("heavy traffic", "light traffic"),
    "is_night": ("night", "daylight"),
    "is_peak_hour": ("peak hour", "off-peak"),
    "is_weekend": ("weekend", "weekday"),
    "hour": ("time of day", "time of day"),
    "solar_elev": ("low sun / darkness", "daylight"),
    "hist_severe_3y": ("crash history here", "little crash history"),
    "is_blackspot": ("declared black spot", "not a black spot"),
    "road_class": ("road class", "road class"),
    "is_urban": ("urban road", "rural road"),
    "district_fatal_share": ("district fatality rate", "district fatality rate"),
    "district_vru_share": ("two/three-wheeler risk", "two/three-wheeler risk"),
    "exposure": ("high traffic exposure", "low traffic exposure"),
}


def load_model() -> lgb.Booster:
    return lgb.Booster(model_file=str(ARTIFACTS / "risk_model_v1.txt"))


def top_factors(model: lgb.Booster, X: pd.DataFrame, k: int = 3) -> list[list[dict]]:
    """Per-row top-k RISK-INCREASING contributors.

    Only positive contributions are surfaced: a driver needs to know what makes
    this stretch dangerous, not what makes it safe.
    """
    contrib = model.predict(X, pred_contrib=True)      # (n, n_feat + 1)
    feats = list(X.columns)
    vals = contrib[:, :-1]
    out = []
    for i in range(len(X)):
        order = np.argsort(-vals[i])[:k]
        row = []
        for j in order:
            if vals[i, j] <= 0:
                continue
            name = feats[j]
            pos, neg = PHRASE.get(name, (name, name))
            row.append({"feature": name, "phrase": pos,
                        "contribution": float(vals[i, j])})
        out.append(row)
    return out


def global_shap(model: lgb.Booster, X: pd.DataFrame, n: int = 40_000) -> pd.DataFrame:
    """Mean |SHAP| per feature, on a sample."""
    Xs = X.sample(min(n, len(X)), random_state=0)
    contrib = model.predict(Xs, pred_contrib=True)[:, :-1]
    s = pd.Series(np.abs(contrib).mean(axis=0), index=list(X.columns))
    return s.sort_values(ascending=False).to_frame("mean_abs_shap")


def main():
    model = load_model()
    df = load_panel()
    feats = json.loads((ARTIFACTS / "risk_features.json").read_text())["features"]
    X = df[feats]

    g = global_shap(model, X)
    g.to_csv(REPORTS / "risk_shap_global.csv")
    print("global mean |SHAP| (top 15):")
    print(g.head(15).round(5).to_string())

    # Worked examples: the riskiest cells, with their plain-language reasons.
    p = model.predict(X, num_iteration=model.best_iteration)
    idx = np.argsort(-p)[:2000]
    tf = top_factors(model, X.iloc[idx[:8]])
    print("\nhighest-risk segment-hours and the reasons a driver would hear:")
    for r, (i, factors) in enumerate(zip(idx[:8], tf)):
        row = df.iloc[i]
        why = ", ".join(f["phrase"] for f in factors) or "(no positive drivers)"
        print(f"  {r+1}. {row['district'][:18]:18s} {row['road_class']:11s} "
              f"h{int(row['hour']):02d} {str(row['weather']):5s} "
              f"score={p[i]:.4f}  ->  {why}")

    # Reason frequency across the flagged top 1% -- what the product would
    # actually be telling drivers most often.
    tf_all = top_factors(model, X.iloc[idx])
    from collections import Counter
    c = Counter(f["phrase"] for row in tf_all for f in row)
    print("\nmost common warning reasons across the flagged top 1%:")
    for phrase, n in c.most_common(10):
        print(f"  {n:5d}  {phrase}")

    (REPORTS / "risk_reason_frequency.json").write_text(
        json.dumps(dict(c.most_common()), indent=2))


if __name__ == "__main__":
    main()
