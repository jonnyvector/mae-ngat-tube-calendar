"""Build the tubing calendar page: app/index.html (template app/template.html + data).

Usage: .venv/bin/python scripts/build_app.py

Trains scripts/model.py on all history, forecasts each of the next 365 days from today's
dam fill and flow, and embeds that with the daily history. scripts/backtest.py scores
the same model on held-out years; its results (data/backtest.json) are shown on the page.
"""
import datetime as dt
import json
from collections import defaultdict
from itertools import groupby

import features as F
import model as Mdl
import predict as P
from common import (CANAL_MCM, DATA, FIRST_YEAR, GOOD, MAX_INFLOW_MCM, POSSIBLE, ROOT, TUBE_MCM,
                    write_atomic)

MAX_DIP_DAYS = 2      # a dip this short doesn't split a window
MIN_WINDOW_DAYS = 3
MARKER = "/*__DATA__*/null"


def band(p):
    return "good" if p >= GOOD else "possible" if p >= POSSIBLE else None


def windows(fc):
    """Stretches of good odds, and of possible odds, in date order."""
    runs = [[b, list(g)] for b, g in groupby(fc, key=lambda f: band(f["p"]))]
    # absorb short dips between two runs of the same band
    merged = []
    for i, run in enumerate(runs):
        dip = (merged and len(run[1]) <= MAX_DIP_DAYS and i + 1 < len(runs)
               and runs[i + 1][0] == merged[-1][0] and merged[-1][0] is not None)
        if dip or (merged and run[0] == merged[-1][0]):
            merged[-1][1] += run[1]
        else:
            merged.append([run[0], list(run[1])])
    return [{"start": r[0]["date"], "end": r[-1]["date"], "days": len(r), "band": b,
             "p_max": max(x["p"] for x in r), "p_avg": round(sum(x["p"] for x in r) / len(r), 3)}
            for b, r in merged if b and len(r) >= MIN_WINDOW_DAYS]


def month_odds(days):
    m = defaultdict(list)
    for d, v in days.items():
        if not v["derived"] and d.year >= FIRST_YEAR:
            m[d.month].append(v["outflow"] >= TUBE_MCM)
    return [round(sum(m[k]) / len(m[k]), 3) if m[k] else None for k in range(1, 13)]


def history(days, climate, rain):
    """Daily series from 2000 as parallel arrays (compact JSON)."""
    start, end = min(days), max(days)
    cols = {"out": [], "pct": [], "inflow": [], "derived": [], "rain": []}
    for i in range((end - start).days + 1):
        d = start + dt.timedelta(days=i)
        v = days.get(d)
        cols["out"].append(round(v["outflow"], 3) if v else None)
        cols["pct"].append(round(v["pct"], 1) if v else None)
        ok = v and v["inflow"] is not None and v["inflow"] < MAX_INFLOW_MCM
        cols["inflow"].append(round(v["inflow"], 3) if ok else None)
        cols["derived"].append(1 if v and v["derived"] else 0)
        cols["rain"].append(rain.get(d))
    enso = {f"{y}-{m:02d}": [oni, phase] for (y, m), (oni, phase, _) in climate.items() if y >= start.year - 1}
    return {"start": start.isoformat(), **cols, "enso": enso}


def main():
    days = P.load(DATA / "rid_daily.csv", DATA / "dam_stats.csv")
    climate, rain = P.load_climate()
    feats = F.series(days)
    today = max(feats)
    if (max(days) - today).days > 3:
        print(f"WARNING: newest usable reading is {today}, but data runs to {max(days)}; forecasting from {today}")
    rows, y, out, _, _ = Mdl.examples(days, feats)
    fc = Mdl.forecast(Mdl.fit(rows, y, out), today, feats[today])
    now = days[today]
    try:
        backtest = json.loads((DATA / "backtest.json").read_text())
    except FileNotFoundError:
        backtest = None
    enso_now = P.enso_at(climate, today) if climate else None
    data = {
        "generated": dt.date.today().isoformat(),
        "latest": today.isoformat(),
        "now": {"pct": round(now["pct"], 1), "outflow": now["outflow"],
                "inflow": now["inflow"] if now["inflow"] is not None and now["inflow"] < MAX_INFLOW_MCM else None,
                "tubable": now["outflow"] >= TUBE_MCM},
        "enso_now": {"oni": enso_now[0], "phase": enso_now[1]} if enso_now else None,
        "thresholds": {"tube": TUBE_MCM, "good": GOOD, "possible": POSSIBLE, "canal": CANAL_MCM},
        "month_odds": month_odds(days),
        "windows": windows(fc),
        "forecast": fc,
        "history": history(days, climate, rain),
        "backtest": backtest,
    }
    template = (ROOT / "app" / "template.html").read_text()
    if MARKER not in template:
        raise SystemExit(f"app/template.html is missing the data marker {MARKER}")
    path = ROOT / "app" / "index.html"
    write_atomic(path, template.replace(MARKER, json.dumps(data, separators=(",", ":"))))
    print(f"Built {path} ({path.stat().st_size // 1024} KB) from {len(y)} training examples: "
          f"forecast {fc[0]['date']} to {fc[-1]['date']}, {len(data['windows'])} tubing windows")


if __name__ == "__main__":
    main()
