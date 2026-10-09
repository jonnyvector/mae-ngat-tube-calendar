"""Fetch weather and climate drivers for the Mae Ngat catchment.

Usage: python3 scripts/fetch_weather.py   (adds recent days; a full pull only when no CSV exists)

Writes:
  data/weather_daily.csv   date, rain_mm, et0_mm, tmax_c, tmin_c - averaged over points
                           spread across the ~1,281 km2 catchment north of the dam.
                           Source: Open-Meteo historical archive (ERA5 reanalysis),
                           https://open-meteo.com/en/docs/historical-weather-api
  data/climate_monthly.csv year, month, oni, enso, dmi
                           oni: NOAA CPC Oceanic Nino Index (3-month SST anomaly, centred
                           on this month); enso: el_nino (>= +0.5), la_nina (<= -0.5) or
                           neutral. dmi: Indian Ocean Dipole Mode Index (NOAA PSL, HadISST).
"""
import csv
import datetime as dt
import io
import json
import time
import urllib.error
import urllib.request

from common import DATA, write_atomic

# Dam at 19.16N 99.04E; the Mae Ngat catchment runs north/north-east towards Phrao.
POINTS = [(19.20, 99.05), (19.32, 99.00), (19.32, 99.15), (19.45, 99.12)]
OPEN_METEO = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
              "&start_date={start}&end_date={end}&timezone=Asia/Bangkok"
              "&daily=precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max,temperature_2m_min")
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
DMI_URL = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data"
# ONI season label -> its centre month
SEASONS = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
           "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


WEATHER_CSV = DATA / "weather_daily.csv"
WEATHER_FIELDS = ["date", "rain_mm", "et0_mm", "tmax_c", "tmin_c"]
REFETCH_DAYS = 90   # recent reanalysis days get revised, so re-pull this many on each run


def get(url, retries=4):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode()
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500 or attempt == retries - 1:
                raise
        except OSError:
            if attempt == retries - 1:
                raise
        time.sleep(2 ** (attempt + 1))


def weather(start="2000-01-01"):
    end = (dt.date.today() - dt.timedelta(days=6)).isoformat()  # archive lags ~5 days
    url = OPEN_METEO.format(lat=",".join(str(p[0]) for p in POINTS),
                            lon=",".join(str(p[1]) for p in POINTS), start=start, end=end)
    sites = json.loads(get(url))
    if not isinstance(sites, list) or "daily" not in sites[0]:
        raise RuntimeError(f"Open-Meteo returned no data: {str(sites)[:200]}")
    keys = [("rain_mm", "precipitation_sum"), ("et0_mm", "et0_fao_evapotranspiration"),
            ("tmax_c", "temperature_2m_max"), ("tmin_c", "temperature_2m_min")]
    rows = []
    for i, day in enumerate(sites[0]["daily"]["time"]):
        row = {"date": day}
        for out, src in keys:
            vals = [s["daily"][src][i] for s in sites if s["daily"][src][i] is not None]
            row[out] = round(sum(vals) / len(vals), 2) if vals else None
        rows.append(row)
    return rows


def oni():
    out = {}
    for line in get(ONI_URL).splitlines()[1:]:
        p = line.split()
        if len(p) == 4 and p[0] in SEASONS:
            out[(int(p[1]), SEASONS[p[0]])] = float(p[3])
    return out


def dmi():
    out = {}
    for line in get(DMI_URL).splitlines()[1:]:
        p = line.split()
        if len(p) == 13 and p[0].isdigit():
            for m, v in enumerate(p[1:], 1):
                if float(v) > -99:  # -9999 = missing
                    out[(int(p[0]), m)] = float(v)
    return out


def update_weather():
    """Merge freshly pulled days into weather_daily.csv (full pull only when there's no file)."""
    rows = {}
    if WEATHER_CSV.exists():
        with open(WEATHER_CSV, newline="") as f:
            rows = {r["date"]: r for r in csv.DictReader(f)}
    start = (dt.date.fromisoformat(max(rows)) - dt.timedelta(days=REFETCH_DAYS)).isoformat() if rows else "2000-01-01"
    for r in weather(start):
        rows[r["date"]] = r
    buf = io.StringIO()
    w = csv.DictWriter(buf, WEATHER_FIELDS)
    w.writeheader()
    w.writerows(rows[d] for d in sorted(rows))
    write_atomic(WEATHER_CSV, buf.getvalue())
    print(f"{len(rows)} days of catchment weather (to {max(rows)})")


def update_climate():
    o, d = oni(), dmi()
    months = sorted(set(o) | set(d))
    old = DATA / "climate_monthly.csv"
    old_n = sum(1 for _ in open(old)) - 1 if old.exists() else 0
    if not o or not d or len(months) < old_n * 0.95:
        raise RuntimeError(f"ENSO/IOD parse looks wrong ({len(o)} ONI, {len(d)} DMI months vs {old_n} on file); "
                           "NOAA may have changed the file format")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["year", "month", "oni", "enso", "dmi"])
    for ym in months:
        v = o.get(ym)
        phase = "" if v is None else "el_nino" if v >= 0.5 else "la_nina" if v <= -0.5 else "neutral"
        w.writerow([*ym, v if v is not None else "", phase, d.get(ym, "")])
    write_atomic(DATA / "climate_monthly.csv", buf.getvalue())
    print(f"{len(months)} months of ENSO/IOD indices (to {months[-1]})")


def main():
    DATA.mkdir(exist_ok=True)
    failed = []
    for name, step in (("weather", update_weather), ("ENSO/IOD", update_climate)):
        try:
            step()
        except (OSError, ValueError, RuntimeError) as e:  # context data: keep the last good file
            failed.append(name)
            print(f"{name} update failed, keeping the previous file: {e}")
    if len(failed) == 2:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
