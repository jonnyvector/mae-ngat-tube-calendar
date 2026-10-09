"""OCR Mae Ngat dam daily water-situation slides into a CSV.

Usage: python3 scripts/extract.py <image_dir> <out.csv>
       python3 scripts/extract.py <image>      (debug: print one photo's record)

Each slide has a Thai header "สถานการณ์น้ำ ณ วัน... ที่ D <month> YYYY" and
label rows whose values are printed in red. Labels are read with Thai OCR;
values are read from a red-only mask with a digits-only OCR pass, then each
value is matched to the label row at the same height.
"""
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from common import CACHE, ROOT, pct_full

ENV = {**os.environ, "TESSDATA_PREFIX": str(ROOT / "tessdata"), "OMP_THREAD_LIMIT": "1"}
HEADER_FRAC = 0.18  # header band holding the date; may be red, so excluded from value OCR

THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
# label keyword -> field; checked in order, first hit wins. None = known row we skip,
# listed so its numbers aren't claimed by a later, looser keyword.
LABELS = [
    ("สะสม", "rain_cum"), ("เทียบ", "pct"), ("วันนี้", "storage_mcm"), ("เข้า", "inflow_mcm"),
    ("ออก", "outflow_mcm"), ("ฝน", "rain_mm"), ("สูงสุด", None), ("เก็บกัก", None),
]
FIELDS = ["date", "storage_mcm", "pct", "inflow_mcm", "outflow_mcm", "rain_mm", "rain_cum",
          "spill_service_cms", "spill_emergency_cms", "power_cms", "canal_right_cms", "canal_left_cms", "format", "file"]
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def tesseract(path, lang, *args):
    out = subprocess.run(["tesseract", str(path), "-", "-l", lang, *args], capture_output=True, env=ENV)
    if out.returncode != 0:  # e.g. missing tessdata: fail loudly rather than cache every photo as "no stats"
        raise RuntimeError(f"tesseract failed on {path}: {out.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return out.stdout.decode("utf-8", "replace")


def tmpdir():
    d = CACHE / f"ocr_{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ocr_crop(img, box, lang="tha+eng", invert=False, scale=3):
    """OCR a crop given as fractions (x0, y0, x1, y1) of the image; returns text lines."""
    w, h = img.size
    c = img.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    g = c.resize((c.width * scale, c.height * scale), Image.LANCZOS).convert("L")
    if invert:
        g = ImageOps.invert(g)
    tmp = tmpdir() / "crop.png"
    g.save(tmp, compress_level=1)
    return [l for l in tesseract(tmp, lang, "--psm", "6").splitlines() if l.strip()]


def nums_in(line):
    return [float(n.replace(",", "")) for n in NUM.findall(line)]


def extract_infographic(img, rec):
    """2025 format: dam-diagram slide with a pink summary panel (bottom right) and a
    release breakdown in m3/s on the dam (right middle)."""
    for line in ocr_crop(img, (0.58, 0.70, 1, 1)):
        v = nums_in(line)
        if not v:
            continue
        if "เข้าเขื่อน" in line and "สะสม" not in line:
            rec.setdefault("inflow_mcm", v[0] / 1e6 if v[0] > 1000 else v[0])  # usually given in m3
        elif "ออก" in line:
            rec.setdefault("outflow_mcm", v[0] / 1e6 if v[0] > 1000 else v[0])
        elif "ฝน" in line:
            rec.setdefault("rain_mm", v[0])
            if len(v) > 1:
                rec.setdefault("rain_cum", v[1])
        elif "ปริมาณ" in line and "ใช้การ" not in line and "สะสม" not in line and 50 < v[0] < 330:
            rec.setdefault("storage_mcm", v[0])
    for line in ocr_crop(img, (0.72, 0.36, 0.93, 0.6), invert=True):
        # value sits just before the unit "ลบ.ม./วิ"; else last number (labels carry "3." list numbering)
        before_unit = line.split("ลบ")[0] if "ลบ" in line else line
        v = nums_in(re.sub(r"(?<![\d.])[1-5]\s*\.\s+(?=\D)", " ", before_unit))[-1:]
        if not v:
            continue
        low = line.lower()
        if "emerg" in low:
            rec.setdefault("spill_emergency_cms", v[0])
        elif "spill" in low or "service" in low:
            rec.setdefault("spill_service_cms", v[0])
        elif "ไฟฟ้า" in line:
            rec.setdefault("power_cms", v[0])
        elif "ขวา" in line:
            rec.setdefault("canal_right_cms", v[0])
        elif "ซ้าย" in line or "ข้าย" in line:
            rec.setdefault("canal_left_cms", v[0])
    return rec


def tsv(path, lang, extra=()):
    out = tesseract(path, lang, *extra, "-c", "tessedit_create_tsv=1")
    rows = []
    for line in out.splitlines()[1:]:
        p = line.split("\t")
        if len(p) == 12 and p[11].strip():
            rows.append(dict(key=(p[2], p[3], p[4]), x=int(p[6]), y=int(p[7]), w=int(p[8]), h=int(p[9]), text=p[11]))
    return rows


def lines(words):
    groups = {}
    for w in words:
        groups.setdefault(w["key"], []).append(w)
    out = []
    for ws in groups.values():
        ws.sort(key=lambda w: w["x"])
        y0 = min(w["y"] for w in ws)
        y1 = max(w["y"] + w["h"] for w in ws)
        out.append(dict(text="".join(w["text"] for w in ws), x=ws[0]["x"], yc=(y0 + y1) / 2, h=y1 - y0))
    return sorted(out, key=lambda l: l["yc"])


def parse_date(text):
    """Find "<day> <Thai month> [พ.ศ.] <BE year>" in OCR text; returns ISO date or None."""
    for m in re.finditer(r"(\d{1,2})\s*([ก-๛]{3,})\s*(?:พ\s*\.?\s*ศ\s*\.?)?\s*(25\d\d)", text):
        word = m.group(2)
        month = next((v for k, v in THAI_MONTHS.items() if k in word or word in k), None)
        if not month:
            # tolerate OCR noise: month name sharing the most characters, if close enough
            k, month = max(THAI_MONTHS.items(), key=lambda kv: len(set(kv[0]) & set(word)))
            if len(set(k) & set(word)) < len(set(k)) * 0.6:
                continue
        day = int(m.group(1))
        if 1 <= day <= 31:
            return f"{int(m.group(3)) - 543:04d}-{month:02d}-{day:02d}"
    return None


def complete(rec):
    return "storage_mcm" in rec and "inflow_mcm" in rec


def extract(path):
    img = orig = Image.open(path).convert("RGB")
    if img.width < 1200:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    a = np.asarray(img).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    tmp = tmpdir()
    full, red, head = tmp / "full.png", tmp / "red.png", tmp / "head.png"
    img.save(full, compress_level=1)
    Image.fromarray(np.where((r - g > 80) & (r - b > 60), 0, 255).astype("uint8")).save(red, compress_level=1)
    img.convert("L").crop((0, 0, img.width, int(img.height * HEADER_FRAC))).point(
        lambda v: 0 if v < 110 else 255).save(head, compress_level=1)
    date = None
    for psm in ("7", "6"):
        date = parse_date(tesseract(head, "tha", "--psm", psm))
        if date:
            break
    if not date:
        date = parse_date(" ".join(ocr_crop(orig, (0, 0, 1, HEADER_FRAC), lang="tha", scale=1)))
    if not date:
        return None
    label_lines = lines(tsv(full, "tha", ["--psm", "11"]))

    nums = [w for w in tsv(red, "eng", ["--psm", "11", "-c", "tessedit_char_whitelist=0123456789.,"])
            if re.fullmatch(r"[\d,]*\d\.\d+|\d+", w["text"]) and w["y"] > img.height * HEADER_FRAC]
    rec = {"date": date, "file": Path(path).name}
    for lab in label_lines:
        field = next((f for k, f in LABELS if k in lab["text"]), "")
        if not field or field in rec:
            continue
        on_row = sorted((n for n in nums if abs(n["y"] + n["h"] / 2 - lab["yc"]) < max(lab["h"], 20) * 0.8
                         and n["x"] > lab["x"]), key=lambda n: n["x"])
        vals = [float(n["text"].replace(",", "")) for n in on_row]
        if not vals:
            continue
        rec[field] = vals[0]
        if field == "storage_mcm" and len(vals) > 1 and "pct" not in rec:
            rec["pct"] = vals[1]  # older slides: "(104.97 %ของความจุเก็บกัก)" on the same row
        if field == "rain_mm" and len(vals) > 1:
            rec["rain_cum"] = vals[1]
    rec["format"] = "slide"
    if not complete(rec):
        rec = extract_infographic(orig, {"date": date, "file": Path(path).name, "format": "infographic"})
    return rec if complete(rec) else None


def clean(recs):
    """Fix OCR'd dates using photo-ID order, then drop physically impossible values.

    Facebook photo IDs grow with upload time, so a slide's date should sit close to the
    dates of its ID neighbours. A date >20 days off is retried with the year +/-1 (common
    2568/2569 misread), otherwise the record is dropped.
    """
    recs.sort(key=lambda r: int(Path(r["file"]).stem))
    ords = [dt.date.fromisoformat(r["date"]).toordinal() for r in recs]
    kept = []
    for i, r in enumerate(recs):
        near = sorted(ords[max(0, i - 8):i] + ords[i + 1:i + 9])
        if not near:
            continue
        mid = near[len(near) // 2]
        d = dt.date.fromisoformat(r["date"])
        if abs(d.toordinal() - mid) > 20:
            fixed = None
            for dy in (-1, 1):
                try:
                    alt = d.replace(year=d.year + dy)
                except ValueError:
                    continue
                if abs(alt.toordinal() - mid) <= 20:
                    fixed = alt
            if not fixed:
                continue
            r["date"] = fixed.isoformat()
        kept.append(r)
    for r in kept:
        if not 30 <= r.get("storage_mcm", 0) <= 300:
            r["storage_mcm"] = None
        for k, hi in (("inflow_mcm", 30), ("outflow_mcm", 30), ("rain_mm", 250), ("rain_cum", 3000)):
            if r.get(k) is not None and not 0 <= r[k] <= hi:
                r[k] = None
        if r["storage_mcm"]:
            r["pct"] = pct_full(r["storage_mcm"])
    return [r for r in kept if r["storage_mcm"]]


def safe_extract(path):
    """Worker wrapper: one unreadable photo is reported and retried next run, not fatal."""
    try:
        return extract(path), None
    except Exception as e:
        return None, f"{path.name}: {e}"


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    # per-photo results cache (non-stats photos cached as null); delete it after changing the parser
    CACHE.mkdir(exist_ok=True)
    cache_path = CACHE / "extract_cache.jsonl"
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue  # line cut short by an interrupted run; that photo is simply redone
            cache[e["file"]] = e["rec"]
    todo = [p for p in files if p.name not in cache]
    print(f"{len(files)} images, {len(todo)} new", flush=True)
    errors = []
    with ProcessPoolExecutor(max_workers=6) as pool, open(cache_path, "a") as cf:
        cf.write("\n")  # start fresh in case the last run left a partial line
        for i, (p, (rec, err)) in enumerate(zip(todo, pool.map(safe_extract, todo, chunksize=4)), 1):
            if err:
                errors.append(err)
                continue
            cache[p.name] = rec
            cf.write(json.dumps({"file": p.name, "rec": rec}, ensure_ascii=False) + "\n")
            if i % 20 == 0:
                cf.flush()
            if i % 200 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    if errors:
        print(f"{len(errors)} photos failed (not cached, retried next run), e.g. {errors[0]}")
    recs = clean([dict(cache[p.name]) for p in files if cache.get(p.name)])
    recs.sort(key=lambda r: (r["date"], r["file"]))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(recs)
    print(f"{len(recs)} stats slides out of {len(files)} images -> {out}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(extract(sys.argv[1]))
    elif len(sys.argv) == 3:
        main()
    else:
        sys.exit(__doc__)
