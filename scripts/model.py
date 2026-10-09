"""Tubing forecast model: P(tubable) and likely release for any day up to a year ahead.

One gradient-boosted model over (start day, lead) examples, using the signals
scripts/signals.py found to matter in held-out years:
  - time of year of the target day, and lead time
  - dam fill on the start day            (the only signal that helps months ahead)
  - outflow on the start day, 7-day mean  (dominates the first few weeks)
  - mean inflow over the past 30 days
Rain, ENSO and IOD made held-out predictions worse, so they are not used.
"""
import datetime as dt

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

import features as F
from common import TUBE_MCM

FEATURES = ["lead", "t_sin", "t_cos", "fill", "outflow_now", "outflow_7d", "inflow_30d"]
SEASON_ONLY = ["lead", "t_sin", "t_cos"]
TRAIN_LEADS = [1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60, 75, 90, 120, 150, 180, 210, 240, 270, 300, 330, 365]
HORIZON = 365


def matrix(rows, cols=FEATURES):
    return np.array([[r[c] for c in cols] for r in rows], dtype=float)


def classifier():
    return HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=40, random_state=0)


def regressor(q):
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=200, learning_rate=0.05,
                                         max_leaf_nodes=15, min_samples_leaf=40, random_state=0)


def examples(days, feats, step=2, leads=TRAIN_LEADS, until=None):
    """Training rows for start days with reported outflow, and targets with reported outflow
    up to `until`. Returns (rows, tubable, outflow, start_year, target_year)."""
    rows, y, out, s_year, t_year = [], [], [], [], []
    for s in sorted(feats)[::step]:
        for k in leads:
            t = s + dt.timedelta(days=k)
            v = days.get(t)
            if not v or v["derived"] or (until and t > until):
                continue
            rows.append(F.row(k, t, feats[s]))
            y.append(v["outflow"] >= TUBE_MCM)
            out.append(v["outflow"])
            s_year.append(s.year)
            t_year.append(t.year)
    return rows, np.array(y), np.array(out), np.array(s_year), np.array(t_year)


def fit(rows, y, out):
    M = matrix(rows)
    return {"p": classifier().fit(M, y), "median": regressor(0.5).fit(M, out), "q75": regressor(0.75).fit(M, out)}


def forecast(models, start, feat):
    """Daily forecast for start + 1..HORIZON from the start day's features."""
    targets = [start + dt.timedelta(days=k) for k in range(1, HORIZON + 1)]
    M = matrix([F.row(k, t, feat) for k, t in enumerate(targets, 1)])
    p, med, q75 = models["p"].predict_proba(M)[:, 1], models["median"].predict(M), models["q75"].predict(M)
    return [{"date": t.isoformat(), "p": round(float(pi), 3), "median": round(max(float(mi), 0), 3),
             "q75": round(max(float(qi), float(mi), 0), 3)} for t, pi, mi, qi in zip(targets, p, med, q75)]


def held_out_predictions(rows, y, s_year, t_year, cols=FEATURES, years=None):
    """P(tubable) for each example from a model that never saw its year: for each year Y, predict
    the examples that start in Y with a model trained on examples that neither start nor land in
    Y or Y+1 (test targets reach into Y+1, so its days must not be training labels or features)."""
    M = matrix(rows, cols)
    pred = np.full(len(y), np.nan)
    for Y in years if years is not None else sorted(set(s_year)):
        test = s_year == Y
        train = ~np.isin(s_year, (Y, Y + 1)) & ~np.isin(t_year, (Y, Y + 1))
        if test.any():
            pred[test] = classifier().fit(M[train], y[train]).predict_proba(M[test])[:, 1]
    return pred
