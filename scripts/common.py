"""Shared paths and dam constants for the Mae Ngat scripts."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / ".cache"
CAPACITY = 265.0       # normal storage capacity, million m3
TUBE_MCM = 0.8         # dam outflow (million m3/day) at which the river below is tubable
CANAL_MCM = 0.37       # what the irrigation canals take first (2.5 + 1.8 m3/s); the rest goes to the river
MAX_INFLOW_MCM = 60    # RID inflow above this is a unit error (m3 logged as million m3), not a flood
FIRST_YEAR = 2006      # RID reports outflow from 2006
GOOD, POSSIBLE = 0.6, 0.3   # forecast bands: "good odds" and "possible"


def pct_full(storage_mcm):
    return round(storage_mcm / CAPACITY * 100, 2)


def write_atomic(path, text):
    """Replace a file in one step, so an interrupted run never leaves it half-written."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
