"""Per-day features known on a forecast's start day, shared by the model and the signal study."""
import datetime as dt
import math

import numpy as np

import predict as P
from common import FIRST_YEAR, MAX_INFLOW_MCM, TUBE_MCM


def doy(d):
    a = 2 * math.pi * d.timetuple().tm_yday / 365.25
    return math.sin(a), math.cos(a)


def row(lead, target, feat):
    """One model input: lead, time of year of the target day, and the start day's features."""
    s, c = doy(target)
    return {"lead": lead, "t_sin": s, "t_cos": c, **feat}


def series(days, rain=None, climate=None):
    """Feature dict for every day since FIRST_YEAR with reported outflow. Rain and ENSO/IOD
    features are added only when their data is passed (the signal study uses them)."""
    feats = {}
    for d, v in days.items():
        if v["derived"] or d.year < FIRST_YEAR:
            continue
        back = [days.get(d - dt.timedelta(days=i)) for i in range(30)]
        out7 = [b["outflow"] for b in back[:7] if b and not b["derived"]]
        inflow = [b["inflow"] for b in back if b and b["inflow"] is not None and b["inflow"] < MAX_INFLOW_MCM]
        inflow7 = [b["inflow"] for b in back[:7] if b and b["inflow"] is not None and b["inflow"] < MAX_INFLOW_MCM]
        prev30 = back[29]
        f = {
            "fill": v["pct"],
            "fill_trend30": v["pct"] - prev30["pct"] if prev30 else np.nan,
            "tubable_now": float(v["outflow"] >= TUBE_MCM),
            "outflow_now": v["outflow"],
            "outflow_7d": np.mean(out7) if out7 else np.nan,
            "inflow_7d": np.mean(inflow7) if inflow7 else np.nan,
            "inflow_30d": np.mean(inflow) if inflow else np.nan,   # mean, so gaps don't bias it low
        }
        if rain is not None:
            f["rain_30d"] = sum(rain.get(d - dt.timedelta(days=i), 0) for i in range(30))
            f["rain_90d"] = sum(rain.get(d - dt.timedelta(days=i), 0) for i in range(90))
        if climate is not None:
            e = P.enso_at(climate, d - dt.timedelta(days=31))  # ONI is published ~1 month late
            f["oni"] = e[0] if e else np.nan
            f["dmi"] = e[2] if e and e[2] is not None else np.nan
        feats[d] = f
    return feats
