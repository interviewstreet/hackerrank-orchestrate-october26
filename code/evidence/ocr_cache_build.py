"""(Re)build the OCR cache for every PNG listed in the evidence manifest.

Usage (from the repository root)::

    python code/evidence/ocr_cache_build.py            # fill missing entries
    python code/evidence/ocr_cache_build.py --force    # re-run OCR for all images
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence.manifest import load_manifest  # noqa: E402
from evidence.parsers.images import load_ocr  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2] / "dataset"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    rep = load_manifest(args.dataset)
    for ev in rep.files:
        if ev.extension != "png":
            continue
        t0 = time.perf_counter()
        items, source = load_ocr(ev.absolute_path, "force" if args.force else "auto")
        print(f"{ev.file_id} {ev.absolute_path.name}: {len(items)} boxes from {source} in {time.perf_counter() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
