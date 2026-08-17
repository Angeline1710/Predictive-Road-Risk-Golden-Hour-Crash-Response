"""Model B -- segment x hour-of-week road-risk model.

PRIMARY TARGET IS A RATE, NOT A BINARY.
A severe crash on one specific 500 m stretch in one specific hour is a
near-never event (0.34% of cells here). Framing that as classification invites
a model that is 99.7% accurate and useless. Production needs an ORDERING --
which stretches, under tonight's conditions, deserve a warning -- so the
primary model is a LightGBM Poisson regressor on the 3-year severe-crash count,
and the operational metric is Precision@top-1%: of the cells we flag, how many
actually saw crashes. A binary head is trained alongside purely for
comparability with the classification literature.

VALIDATION IS BLOCKED IN SPACE AND TIME.
Weather is drawn per district-hour, so neighbouring segments share conditions.
Random k-fold would put the same district-hour on both sides of the split and
report a flattering number that collapses on a new corridor. Folds hold out
whole DISTRICTS (spatial blocks). A separate temporal split holds out whole
hour-of-day ranges. Both are reported, along with the random-fold number, to
show the size of the gap -- that gap is the point.
"""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_poisson_deviance,
    roc_auc_score,
)
from scipy.stats import spearmanr

from ml.common.config import ARTIFACTS, DATA_PROC, REPORTS, SEED

TARGET_COUNT = "count"
TARGET_BIN = "y"
# Excluded from features: the labels themselves and the generator's ground truth.
LEAK = {TARGET_COUNT, TARGET_BIN, "lam_true", "segment_idx", "frailty", "length_m"}

CAT = ["district", "road_class", "weather", "visibility", "traffic_density"]

PARAMS_POISSON = dict(
    objective="poisson", metric="poisson", learning_rate=0.05,
    num_leaves=63, min_data_in_leaf=200, feature_fraction=0.85,
    bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
    verbose=-1, seed=SEED, num_threads=0,
)
PARAMS_BIN = dict(
    objective="binary", metric="average_precision", learning_rate=0.05,
    num_leaves=63, min_data_in_leaf=200, feature_fraction=0.85,
    bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
    verbose=-1, seed=SEED, num_threads=0,
)


def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PROC / "risk_panel.parquet")
    for c in CAT:
        df[c] = df[c].astype("category")
    return df


def feature_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in LEAK]


def precision_at_k(y_true_count: np.ndarray, score: np.ndarray, k_frac: float) -> dict:
    """Of the top k_frac of cells by predicted risk, what share had a crash,
    and what share of ALL crashes did we capture?"""
    n = len(score)
    k = max(1, int(n * k_frac))
    top = np.argpartition(-score, k)[:k]
    hits = (y_true_count[top] > 0).sum()
    return {
        "precision": float(hits / k),
        "recall_of_crashes": float(y_true_count[top].sum() / max(1, y_true_count.sum())),
        "lift": float((hits / k) / max(1e-12, (y_true_count > 0).mean())),
        "k": int(k),
    }


def _fit(tr: pd.DataFrame, va: pd.DataFrame, feats: list[str], params: dict,
         target: str, rounds: int = 900):
    dtr = lgb.Dataset(tr[feats], tr[target], categorical_feature=CAT, free_raw_data=False)
    dva = lgb.Dataset(va[feats], va[target], categorical_feature=CAT, reference=dtr,
                      free_raw_data=False)
    return lgb.train(params, dtr, num_boost_round=rounds, valid_sets=[dva],
                     callbacks=[lgb.early_stopping(60, verbose=False)])


def eval_fold(model, va: pd.DataFrame, feats: list[str], kind: str) -> dict:
    p = model.predict(va[feats], num_iteration=model.best_iteration)
    yc = va[TARGET_COUNT].to_numpy()
    yb = va[TARGET_BIN].to_numpy()
    out = {"n": int(len(va)), "pos_rate": float(yb.mean()), "best_iter": int(model.best_iteration)}
    if kind == "poisson":
        p = np.clip(p, 1e-9, None)
        out["poisson_deviance"] = float(mean_poisson_deviance(yc, p))
        out["spearman_vs_truth"] = float(spearmanr(va["lam_true"], p).statistic)
    else:
        out["brier"] = float(brier_score_loss(yb, np.clip(p, 0, 1)))
    out["pr_auc"] = float(average_precision_score(yb, p))
    out["roc_auc"] = float(roc_auc_score(yb, p))
    out["spearman_rank"] = float(spearmanr(yc, p).statistic)
    for kf, name in ((0.001, "p@0.1%"), (0.01, "p@1%"), (0.05, "p@5%")):
        out[name] = precision_at_k(yc, p, kf)
    return out


def cv_spatial(df: pd.DataFrame, feats: list[str], n_folds: int = 5,
               kind: str = "poisson") -> list[dict]:
    """Hold out whole districts. This is the number that matters."""
    params = PARAMS_POISSON if kind == "poisson" else PARAMS_BIN
    target = TARGET_COUNT if kind == "poisson" else TARGET_BIN
    dists = df["district"].cat.categories.tolist()
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(dists))
    folds = np.array_split(order, n_folds)
    res = []
    for i, f in enumerate(folds):
        held = {dists[j] for j in f}
        m = df["district"].isin(held)
        tr, va = df[~m], df[m]
        model = _fit(tr, va, feats, params, target)
        r = eval_fold(model, va, feats, kind)
        r.update(fold=i, held_districts=len(held))
        res.append(r)
        print(f"    spatial fold {i}: {len(held)} districts held, "
              f"PR-AUC={r['pr_auc']:.4f}  p@1%={r['p@1%']['precision']:.4f}")
    return res


def cv_temporal(df: pd.DataFrame, feats: list[str], kind: str = "poisson") -> list[dict]:
    """Hold out whole hour-of-day blocks."""
    params = PARAMS_POISSON if kind == "poisson" else PARAMS_BIN
    target = TARGET_COUNT if kind == "poisson" else TARGET_BIN
    blocks = [range(0, 6), range(6, 12), range(12, 18), range(18, 24)]
    res = []
    for i, b in enumerate(blocks):
        m = df["hour"].isin(list(b))
        tr, va = df[~m], df[m]
        model = _fit(tr, va, feats, params, target)
        r = eval_fold(model, va, feats, kind)
        r.update(fold=i, hours=f"{b.start:02d}-{b.stop:02d}")
        res.append(r)
        print(f"    temporal fold {b.start:02d}-{b.stop:02d}h: "
              f"PR-AUC={r['pr_auc']:.4f}  p@1%={r['p@1%']['precision']:.4f}")
    return res


def cv_random(df: pd.DataFrame, feats: list[str], kind: str = "poisson",
              n_folds: int = 5) -> list[dict]:
    """Random k-fold -- reported ONLY to quantify how much it overstates."""
    params = PARAMS_POISSON if kind == "poisson" else PARAMS_BIN
    target = TARGET_COUNT if kind == "poisson" else TARGET_BIN
    rng = np.random.default_rng(SEED)
    fold = rng.integers(0, n_folds, len(df))
    res = []
    for i in range(n_folds):
        m = fold == i
        model = _fit(df[~m], df[m], feats, params, target)
        r = eval_fold(model, df[m], feats, kind)
        r["fold"] = i
        res.append(r)
    return res


def agg(rs: list[dict]) -> dict:
    keys = [k for k, v in rs[0].items() if isinstance(v, (int, float))]
    out = {k: float(np.mean([r[k] for r in rs])) for k in keys}
    out["pr_auc_sd"] = float(np.std([r["pr_auc"] for r in rs]))
    for name in ("p@0.1%", "p@1%", "p@5%"):
        out[name] = {kk: float(np.mean([r[name][kk] for r in rs]))
                     for kk in rs[0][name]}
    return out


def main(sample: int | None = 2_500_000) -> dict:
    df = load_panel()
    if sample and len(df) > sample:
        # Stratified downsample: keep every positive, subsample negatives.
        # Positives are 0.34% of 6.7M; keeping all of them preserves the signal
        # while making 5-fold x 3 CV designs tractable.
        pos = df.index[df[TARGET_BIN] == 1]
        neg = df.index[df[TARGET_BIN] == 0]
        rng = np.random.default_rng(SEED)
        keep_neg = rng.choice(neg, size=min(len(neg), sample - len(pos)), replace=False)
        df = df.loc[np.concatenate([pos, keep_neg])].sample(frac=1, random_state=SEED)
        print(f"downsampled to {len(df):,} rows (all {len(pos):,} positives kept)")

    feats = feature_cols(df)
    print(f"features ({len(feats)}): {feats}\n")

    out = {"n_rows": int(len(df)), "n_features": len(feats), "features": feats,
           "pos_rate": float(df[TARGET_BIN].mean())}

    print("  Poisson / spatial-blocked CV")
    sp = cv_spatial(df, feats, kind="poisson")
    print("  Poisson / temporal-blocked CV")
    tp = cv_temporal(df, feats, kind="poisson")
    print("  Poisson / random CV (optimistic reference)")
    rp = cv_random(df, feats, kind="poisson")
    print("  Binary / spatial-blocked CV")
    sb = cv_spatial(df, feats, kind="binary")

    out["poisson_spatial"] = agg(sp)
    out["poisson_temporal"] = agg(tp)
    out["poisson_random"] = agg(rp)
    out["binary_spatial"] = agg(sb)
    out["optimism_gap_pr_auc"] = (out["poisson_random"]["pr_auc"]
                                  - out["poisson_spatial"]["pr_auc"])

    # ---- final model on everything, for serving + SHAP -------------------
    print("\n  fitting final model")
    n = len(df)
    cut = int(n * 0.85)
    final = _fit(df.iloc[:cut], df.iloc[cut:], feats, PARAMS_POISSON, TARGET_COUNT)
    final.save_model(str(ARTIFACTS / "risk_model_v1.txt"))
    out["final_best_iter"] = int(final.best_iteration)

    imp = pd.Series(final.feature_importance("gain"), index=feats).sort_values(ascending=False)
    out["gain_importance"] = {k: float(v) for k, v in imp.head(20).items()}

    # ---- risk bands from predicted-rate quantiles -------------------------
    p = final.predict(df[feats], num_iteration=final.best_iteration)
    q = np.quantile(p, [0.50, 0.85, 0.97])
    out["band_thresholds"] = {"Low<": float(q[0]), "Moderate<": float(q[1]),
                              "High<": float(q[2]), "Severe>=": float(q[2])}
    band = np.digitize(p, q)
    obs = df[TARGET_COUNT].to_numpy()
    out["band_observed_rate"] = {
        n_: float((obs[band == i] > 0).mean()) if (band == i).any() else None
        for i, n_ in enumerate(["Low", "Moderate", "High", "Severe"])}

    (ARTIFACTS / "risk_features.json").write_text(json.dumps({"features": feats, "cat": CAT}))
    return out


if __name__ == "__main__":
    r = main()
    (REPORTS / "risk_model_results.json").write_text(json.dumps(r, indent=2, default=float))
    print("\n" + "=" * 72)
    for k in ("poisson_spatial", "poisson_temporal", "poisson_random", "binary_spatial"):
        v = r[k]
        print(f"{k:20s} PR-AUC {v['pr_auc']:.4f} (sd {v['pr_auc_sd']:.4f})  "
              f"p@1% {v['p@1%']['precision']:.4f}  lift {v['p@1%']['lift']:.1f}x")
    print(f"\noptimism gap (random - spatial) PR-AUC: {r['optimism_gap_pr_auc']:+.4f}")
    print(f"\nband observed crash rates: {r['band_observed_rate']}")
    print(f"\ntop features: {list(r['gain_importance'])[:8]}")
