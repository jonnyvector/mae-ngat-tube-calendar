"""Find which signals predict a tubable river, and how far ahead.

Usage: .venv/bin/python scripts/signals.py

Uses the model's (start day, lead) examples with every candidate signal known on the start
day, and the model's leak-free held-out test (each year predicted by a model that saw none
of its starts or outcomes). Each feature set is scored by Brier score, per lead range:
  - season only: target day-of-year + lead (what a calendar average knows)
  - + one signal: how much each single signal adds on top of the season
  - all signals, and all signals minus each one
"""
import datetime as dt

import numpy as np

import features as F
import model as Mdl
import predict as P
from common import DATA

LEADS = [1, 3, 7, 14, 21, 30, 45, 60, 90, 120, 150, 180, 240, 300, 365]
RANGES = {"1-7 days": (1, 7), "2-4 weeks": (14, 30), "1-3 months": (45, 90), "4-12 months": (120, 365)}
SIGNALS = ["fill", "fill_trend30", "tubable_now", "outflow_now", "outflow_7d", "inflow_7d", "inflow_30d",
           "rain_30d", "rain_90d", "oni", "dmi"]


def main():
    days = P.load(DATA / "rid_daily.csv", DATA / "dam_stats.csv")
    climate, rain = P.load_climate()
    feats = F.series(days, rain, climate)
    until = dt.date(max(days).year - 1, 12, 31)   # last complete year
    rows, y, _, s_year, t_year = Mdl.examples(days, feats, step=3, leads=LEADS, until=until)
    leads = np.array([r["lead"] for r in rows])
    masks = {name: (leads >= a) & (leads <= b) for name, (a, b) in RANGES.items()}
    print(f"{len(y)} examples from {len(set(s_year))} years; {y.mean():.0%} tubable\n")

    def brier(cols):
        p = Mdl.held_out_predictions(rows, y, s_year, t_year, cols=cols)
        return {r: float(np.nanmean((p[m] - y[m]) ** 2)) for r, m in masks.items()}

    base = brier(Mdl.SEASON_ONLY)
    full = brier(Mdl.SEASON_ONLY + SIGNALS)
    print("Skill over season-only (higher = more useful; 0 = adds nothing)")
    print(f"{'':28s}" + "".join(f"{r:>14s}" for r in RANGES))
    print(f"{'season only (Brier)':28s}" + "".join(f"{base[r]:14.3f}" for r in RANGES))
    print(f"{'ALL signals':28s}" + "".join(f"{1 - full[r] / base[r]:+14.0%}" for r in RANGES))
    print("\nSeason + one signal:")
    for s in SIGNALS:
        b = brier(Mdl.SEASON_ONLY + [s])
        print(f"  {s:26s}" + "".join(f"{1 - b[r] / base[r]:+14.0%}" for r in RANGES))
    print("\nAll signals minus one (how much is lost without it):")
    for s in SIGNALS:
        b = brier(Mdl.SEASON_ONLY + [x for x in SIGNALS if x != s])
        print(f"  - {s:24s}" + "".join(f"{(full[r] - b[r]) / base[r]:+14.1%}" for r in RANGES))


if __name__ == "__main__":
    main()
