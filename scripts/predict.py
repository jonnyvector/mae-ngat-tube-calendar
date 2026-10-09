"""Forecast Mae Ngat dam river releases from the daily history.

Usage: python3 scripts/predict.py [--days 60] [--rid data/rid_daily.csv] [--fb data/dam_stats.csv]

Method (analog forecasting): find past days that looked like today - same time of
year (+/-WINDOW days), similar fill level (+/-PCT_BAND points) and the same release
state - then follow each of them forward and count how often the dam released water
into the river over the following weeks. Every past year contributes; probabilities
are reported with how many distinct years back them.
"""
import argparse
import csv
import datetime as dt
import sys
from collections import defaultdict
from statistics import median_low
from pathlib import Path

from common import CAPACITY, DATA, MAX_INFLOW_MCM
# น้ำออกเขื่อน (total outflow) fills three paths in order: irrigation canals first
# (~2.5 + 1.8 m3/s = ~0.37 M m3/day), then the river outlet (power plant), then the spillway.
RIVER_MCM = 0.45     # outflow above this (million m3/day) means water is going into the river
                     # (canals take ~0.37, common.RIVER_MCM; 0.45 leaves a margin for reporting noise)
HIGH_MCM = 1.5       # big river release
WINDOW = 15          # +/- days of year for analogs
PCT_BAND = 8.0       # +/- fill-level points for analogs
CMS_TO_MCM_DAY = 0.0864


def read_rows(path):
    by_date = {}
    try:
        f = open(path, newline="")
    except FileNotFoundError:
        return by_date
    with f:
        for r in csv.DictReader(f):
            if num(r.get("storage_mcm")) is None:
                continue
            d = dt.date.fromisoformat(r["date"])
            # several photos can carry the same day; keep the most complete reading
            filled = sum(1 for v in r.values() if v)
            if d not in by_date or filled > by_date[d][1]:
                by_date[d] = (r, filled)
    return {d: r for d, (r, _) in by_date.items()}


def num(v):
    return float(v) if v not in (None, "", "None") else None  # RID writes "None" for missing


def load(rid_path, fb_path):
    """Merge RID daily history (long record) with Facebook slide data (recent, has the
    release breakdown). RID wins where both exist. A missing outflow is derived from the
    water balance (outflow = inflow - change in storage) and marked derived; derived days
    are kept for context but not used for release statistics."""
    rid, fb = read_rows(rid_path), read_rows(fb_path)
    days = {}
    for d in sorted(set(rid) | set(fb)):
        r = rid.get(d) or fb[d]
        f = fb.get(d, {})
        storage = num(r["storage_mcm"])
        inflow = num(r.get("inflow_mcm"))
        if inflow is None:
            inflow = num(f.get("inflow_mcm"))
        outflow = num(r.get("outflow_mcm"))
        if outflow is None:
            outflow = num(f.get("outflow_mcm"))
        spill = None
        service, emergency = num(f.get("spill_service_cms")), num(f.get("spill_emergency_cms"))
        # trust the spillway breakdown only when both values were read and fit inside total outflow
        if service is not None and emergency is not None and outflow is not None:
            if (service + emergency) * CMS_TO_MCM_DAY <= outflow + 0.05:
                spill = service + emergency
        days[d] = dict(storage=storage, pct=storage / CAPACITY * 100, inflow=inflow,
                       outflow=outflow, derived=False, spill=spill)
    for d, v in days.items():
        prev = days.get(d - dt.timedelta(days=1))
        if v["outflow"] is None and prev and v["inflow"] is not None and v["inflow"] < MAX_INFLOW_MCM:
            v["outflow"] = max(v["inflow"] - (v["storage"] - prev["storage"]), 0.0)
            v["derived"] = True
    return {d: v for d, v in days.items() if v["outflow"] is not None}


def doy_dist(a, b):
    d = abs(a.timetuple().tm_yday - b.timetuple().tm_yday)
    return min(d, 365 - d)


def releasing(v):
    return v["outflow"] > RIVER_MCM


def monthly_profile(days):
    m = defaultdict(list)
    for d, v in days.items():
        if not v["derived"]:
            m[d.month].append(v)
    return {k: (sum(map(releasing, vs)) / len(vs), median_low(v["outflow"] for v in vs), len(vs))
            for k, vs in sorted(m.items())}


def analog_starts(days, today, now, usable=None, on=None):
    """Past days resembling today: one best match (closest fill) per year. `usable(d)` limits
    which days may serve as analogs (default: at least 60 days before today); `on(v)` is the
    state an analog must share with today (default: river release or not)."""
    on = on or releasing
    usable = usable or (lambda d: d <= today - dt.timedelta(days=60))
    best = {}
    for d, v in days.items():
        if v["derived"] or not usable(d):
            continue
        if doy_dist(d, today) > WINDOW or abs(v["pct"] - now["pct"]) > PCT_BAND:
            continue
        if on(v) != on(now):
            continue
        score = abs(v["pct"] - now["pct"]) + doy_dist(d, today) * 0.2
        key = round((today - d).days / 365.25)  # which past year's season this day belongs to
        if key not in best or score < best[key][0]:
            best[key] = (score, d)
    return sorted(d for _, d in best.values())


def load_climate():
    """Monthly ENSO/IOD and daily catchment weather from scripts/fetch_weather.py (optional)."""
    climate, rain = {}, {}
    try:
        with open(DATA / "climate_monthly.csv", newline="") as f:
            for r in csv.DictReader(f):
                if r["oni"]:
                    climate[(int(r["year"]), int(r["month"]))] = (float(r["oni"]), r["enso"], num(r["dmi"]))
        with open(DATA / "weather_daily.csv", newline="") as f:
            for r in csv.DictReader(f):
                if r["rain_mm"]:
                    rain[dt.date.fromisoformat(r["date"])] = float(r["rain_mm"])
    except FileNotFoundError:
        pass
    return climate, rain


def enso_at(climate, d):
    """Latest ENSO reading at or before date d (ONI is published with a ~1 month lag)."""
    for back in range(0, 4):
        y, m = (d.year, d.month - back) if d.month > back else (d.year - 1, d.month - back + 12)
        if (y, m) in climate:
            return climate[(y, m)]
    return None


def print_climate(climate, rain, today):
    if not climate:
        return
    oni, phase, dmi = enso_at(climate, today)
    label = {"el_nino": "El Nino", "la_nina": "La Nina", "neutral": "ENSO-neutral"}[phase]
    print(f"Climate: {label} (ONI {oni:+.2f})" + (f", Indian Ocean Dipole {dmi:+.2f}" if dmi is not None else ""))
    print("  History: El Nino rainy seasons add ~80 M m3 to storage vs ~110 neutral and ~140 La Nina,")
    print("  so El Nino years end fuller less often and release less in Aug-Dec.")
    if phase == "el_nino" and oni >= 1.5:
        print(f"  A strong El Nino usually lingers into next year: higher risk of a weak {today.year + 1} rainy")
        print("  season and a low dam (the 2015 El Nino left it only 23% full by November).")
    if rain:
        last = max(rain)
        for span in (30, 90):
            recent = sum(rain.get(last - dt.timedelta(days=i), 0) for i in range(span))
            normal = [sum(rain.get(dt.date(y, last.month, last.day) - dt.timedelta(days=i), 0) for i in range(span))
                      for y in range(min(rain).year + 1, last.year)]
            print(f"  Catchment rain, last {span} days to {last}: {recent:.0f} mm "
                  f"(normal {sorted(normal)[len(normal) // 2]:.0f} mm)")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rid", default=str(DATA / "rid_daily.csv"))
    ap.add_argument("--fb", default=str(DATA / "dam_stats.csv"))
    ap.add_argument("--days", type=int, default=60)
    a = ap.parse_args()

    days = load(a.rid, a.fb)
    if not days:
        sys.exit("No data found; run ./refresh first.")
    today = max(days)
    now = days[today]
    first = min((d for d in days if d >= today - dt.timedelta(days=7)), default=today)
    trend = (now["storage"] - days[first]["storage"]) / max((today - first).days, 1)

    reported = sum(not v["derived"] for v in days.values())
    print(f"History: {min(days)} to {today}, {reported} days with reported outflow")
    print(f"Latest {today}: {now['storage']:.3f} M m3 ({now['pct']:.1f}% full), "
          f"in {now['inflow'] if now['inflow'] is not None else float('nan'):.3f}, out {now['outflow']:.3f} M m3/day, storage {trend:+.3f}/day over the last week")
    state = "RELEASING into the river" if releasing(now) else "canals only (no river release)"
    if now["spill"]:
        state += f", SPILLWAY {now['spill']:.1f} m3/s"
    print(f"Current state: {state}\n")
    stale = (dt.date.today() - today).days
    if stale > 2:
        print(f"WARNING: latest data is {stale} days old; run ./refresh. The forecast counts from {today}.\n")

    print(f"Month  share of days with river release (>{RIVER_MCM})  median outflow")
    for mo, (p, med, n) in monthly_profile(days).items():
        print(f"{dt.date(2000, mo, 1):%b}    {p:6.0%}                                   {med:6.3f}")
    known = [v["spill"] for v in days.values() if v["spill"] is not None]
    if known:
        print(f"Spillway: used on {sum(s > 0 for s in known)} of {len(known)} days with a release breakdown")
    print()

    climate, rain = load_climate()
    print_climate(climate, rain, today)

    starts = analog_starts(days, today, now)
    print(f"Analog years: {len(starts)} past seasons that looked like today "
          f"(+/-{WINDOW} days of the date, +/-{PCT_BAND:.0f} pts fill, same release state):")
    def tag(d):
        e = enso_at(climate, d)
        return f"{d} ({days[d]['pct']:.0f}%" + (f", {e[1].replace('_', ' ')}" if e else "") + ")"
    print("  " + ", ".join(tag(d) for d in starts))
    if not starts:
        print("No analogs found; widen WINDOW or PCT_BAND.")
        return
    print()

    print(f"Week starting   P(any river release that week)   P(big release >{HIGH_MCM})")
    for k in range(1, a.days + 1, 7):
        any_rel = big = n = 0
        for s in starts:
            vals = [days[s + dt.timedelta(days=j)] for j in range(k, k + 7)
                    if s + dt.timedelta(days=j) in days and not days[s + dt.timedelta(days=j)]["derived"]]
            if not vals:
                continue
            n += 1
            any_rel += any(releasing(v) for v in vals)
            big += any(v["outflow"] > HIGH_MCM for v in vals)
        if n:
            print(f"{today + dt.timedelta(days=k)}      {any_rel / n:6.0%}                            {big / n:6.0%}")

    firsts = []
    for s in starts:
        for j in range(1, a.days + 1):
            v = days.get(s + dt.timedelta(days=j))
            if v and not v["derived"] and releasing(v) != releasing(now):
                firsts.append(j)
                break
    change = "start releasing into the river" if not releasing(now) else "drop back to canals only"
    print()
    print(f"In {len(firsts)} of {len(starts)} analog years the dam went on to {change} within {a.days} days", end="")
    if firsts:
        firsts.sort()
        print(f"; median after {firsts[len(firsts) // 2]} days "
              f"(around {today + dt.timedelta(days=firsts[len(firsts) // 2])}), "
              f"earliest after {firsts[0]}, latest after {firsts[-1]}.")
    else:
        print(".")


if __name__ == "__main__":
    main()
