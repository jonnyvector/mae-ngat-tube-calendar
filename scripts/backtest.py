"""Backtest the tubing forecast model on years it never saw.

Usage: .venv/bin/python scripts/backtest.py

Every (start day, lead) example up to the last complete year is predicted by a model that
saw none of that year's starts or outcomes, then checked against whether the target day
was tubable. Compared with a season-only model (time of year + lead: a smart calendar
average). Reports per lead: hit rate at a 50% cut, Brier skill vs season-only, and how
often days in each calendar band (good odds / possible / unlikely) turned out tubable.
Saves data/backtest.json for the page.
"""
import datetime as dt
import json

import numpy as np

import features as F
import model as Mdl
import predict as P
from common import DATA, GOOD, POSSIBLE, TUBE_MCM, write_atomic

REPORT = [1, 7, 14, 30, 60, 120, 240, 365]


def pct(x):
    return "  -  " if x is None else f"{x:4.0%}"


def main():
    days = P.load(DATA / "rid_daily.csv", DATA / "dam_stats.csv")
    feats = F.series(days)
    last_year = max(days).year - 1
    rows, y, _, s_year, t_year = Mdl.examples(days, feats, step=3, until=dt.date(last_year, 12, 31))
    leads = np.array([r["lead"] for r in rows])
    pred = Mdl.held_out_predictions(rows, y, s_year, t_year)
    base = Mdl.held_out_predictions(rows, y, s_year, t_year, cols=Mdl.SEASON_ONLY)

    print(f"{len(y)} examples starting {min(s_year)}-{last_year}, each year predicted by a model that saw "
          f"none of it. Tubable = outflow >= {TUBE_MCM}\n")
    print("Lead   Hit rate  Skill vs season-only  Good odds->tubable  Possible->tubable  Unlikely->tubable    n")
    results = []
    for k in REPORT:
        m = (leads == k) & ~np.isnan(pred)
        if not m.any():
            continue
        p, b, o = pred[m], base[m], y[m]
        bands = {"good": o[p >= GOOD], "possible": o[(p >= POSSIBLE) & (p < GOOD)], "unlikely": o[p < POSSIBLE]}
        rate = {n: (round(float(v.mean()), 3) if len(v) else None) for n, v in bands.items()}
        res = {"lead_days": k, "hit_rate": round(float(np.mean((p >= 0.5) == o)), 3),
               "skill_vs_calendar": round(float(1 - np.mean((p - o) ** 2) / np.mean((b - o) ** 2)), 3),
               "band_rate": rate, "n": int(m.sum())}
        results.append(res)
        print(f"+{k:<4d}  {res['hit_rate']:5.0%}      {res['skill_vs_calendar']:+6.0%}              "
              f"{pct(rate['good'])}               {pct(rate['possible'])}              {pct(rate['unlikely'])}       {res['n']}")
    write_atomic(DATA / "backtest.json", json.dumps(
        {"run": dt.date.today().isoformat(), "threshold": TUBE_MCM, "years": [int(min(s_year)), last_year],
         "leads": results}, indent=1))


if __name__ == "__main__":
    main()
