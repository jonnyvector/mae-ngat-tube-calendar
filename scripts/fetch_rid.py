"""Fetch Mae Ngat dam daily data from the Royal Irrigation Department public API.

Usage: python3 scripts/fetch_rid.py [--full]

API: https://app.rid.go.th/reservoir/api/dam/public/<date> (docs: .../api/document/dam),
listed on data.go.th as dataset big_dams_public. One request per day returns all large
dams; we keep Mae Ngat (id 200103).

data/rid_daily.csv is the store (storage/inflow/outflow in million m3). Each run adds the
days it doesn't have yet, retrying gaps from the last 60 days; --full retries every
missing day back to 2000. A fresh checkout with no CSV fetches everything (~30 min).
"""
import csv
import datetime as dt
import http.client
import io
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import DATA, write_atomic

URL = "https://app.rid.go.th/reservoir/api/dam/public/{}"
DAM_ID = "200103"
FIRST_DAY = dt.date(2000, 1, 1)
RETRY_WINDOW = 60
RETRIES = 4
REFRESH_LAST = 3      # always re-fetch the newest days on file
FIELDS = ["date", "storage_mcm", "pct", "inflow_mcm", "outflow_mcm"]
OUT = DATA / "rid_daily.csv"


def mae_ngat(doc):
    for region in doc.get("data") or []:
        for d in region.get("dam") or []:
            if isinstance(d, dict) and str(d.get("id")) == DAM_ID and d.get("volume") is not None:
                return d
    return None


def fetch(day):
    """("ok", row), ("empty", None) when the API has no Mae Ngat reading for the day,
    or ("error", None) when the request kept failing."""
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(URL.format(day), timeout=15) as r:
                d = mae_ngat(json.loads(r.read()))
            if d is None:
                return "empty", None
            return "ok", {"date": day, "storage_mcm": d["volume"], "pct": d.get("percent_storage"),
                          "inflow_mcm": d.get("inflow"), "outflow_mcm": d.get("outflow")}
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return "empty", None  # no such day; retrying won't help
        except (OSError, ValueError, KeyError, TypeError, AttributeError, http.client.HTTPException):
            pass
        if attempt < RETRIES - 1:
            time.sleep(2 * (attempt + 1))
    return "error", None


def main():
    rows = {}
    if OUT.exists():
        with open(OUT, newline="") as f:
            rows = {r["date"]: r for r in csv.DictReader(f)}
    today = dt.date.today()
    every = [(FIRST_DAY + dt.timedelta(n)).isoformat() for n in range((today - FIRST_DAY).days + 1)]
    # missing days, plus the newest few on file in case an early-morning reading was provisional
    todo = sorted({d for d in every if d not in rows} | set(sorted(rows)[-REFRESH_LAST:]))
    if rows and "--full" not in sys.argv:
        since = (dt.date.fromisoformat(max(rows)) - dt.timedelta(days=RETRY_WINDOW)).isoformat()
        todo = [d for d in todo if d >= since]
    print(f"{len(rows)} days on file, fetching {len(todo)}", flush=True)
    added, errors = 0, []
    with ThreadPoolExecutor(max_workers=4) as pool:  # kept low to be polite to a government API
        for i, (day, (status, row)) in enumerate(zip(todo, pool.map(fetch, todo)), 1):
            if status == "ok":
                added += day not in rows
                rows[day] = row
            elif status == "error":
                errors.append(day)
            if i % 250 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    if errors:
        print(f"{len(errors)} days failed to download (retried next run), e.g. {errors[:3]}")
    if todo and len(errors) == len(todo):
        raise SystemExit("Every request to the RID API failed; leaving data/rid_daily.csv unchanged.")
    if not rows:
        raise SystemExit("No Mae Ngat data on file or from the API; nothing written.")
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS)
    w.writeheader()
    w.writerows(rows[d] for d in sorted(rows))
    DATA.mkdir(exist_ok=True)
    write_atomic(OUT, buf.getvalue())
    print(f"added {added} days; {len(rows)} days with Mae Ngat data -> {OUT} (latest {max(rows)})")


if __name__ == "__main__":
    main()
