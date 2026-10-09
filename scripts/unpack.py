"""Unpack browser-saved photo batches (~/Downloads/maengad_batch_*.json) into data/raw/<fbid>.<ext>.

Usage: python3 scripts/unpack.py [--delete]   (--delete removes each batch file once unpacked)
"""
import base64
import json
import sys
from pathlib import Path

from common import DATA

RAW = DATA / "raw"
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def main():
    delete = "--delete" in sys.argv
    RAW.mkdir(parents=True, exist_ok=True)
    for batch in sorted((Path.home() / "Downloads").glob("maengad_batch_*.json")):
        with open(batch) as f:
            items = json.load(f)
        saved, failed = 0, []
        for it in items:
            if not it.get("data"):  # the browser failed to fetch this photo
                failed.append(it["id"])
                continue
            head, b64 = it["data"].split(",", 1)
            ext = EXT.get(head.removeprefix("data:").split(";")[0])
            if not ext:
                failed.append(it["id"])
                continue
            (RAW / f"{it['id']}.{ext}").write_bytes(base64.b64decode(b64))
            saved += 1
        if failed:  # keep a record so these photo IDs can be fetched by hand later
            with open(RAW.parent / "failed_photo_ids.txt", "a") as f:
                f.writelines(f"{i}\n" for i in failed)
        print(f"{batch.name}: {saved} of {len(items)} photos saved"
              + (f", {len(failed)} failed (listed in data/failed_photo_ids.txt)" if failed else ""))
        if delete:
            batch.unlink()


if __name__ == "__main__":
    main()
