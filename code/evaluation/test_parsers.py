#!/usr/bin/env python3
"""Parser test: load all evidence, report facts per file / format."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.config import DEFAULT_DATASET_DIR              # noqa: E402
from audit.loaders import load_dataset                    # noqa: E402
from audit.parsers import build_fact_store                # noqa: E402


def main():
    data = load_dataset(DEFAULT_DATASET_DIR)
    store, stats = build_fact_store(DEFAULT_DATASET_DIR, data["evidence_files"])
    print(f"Total facts: {len(store.facts)} from {len(stats)} files")
    zero = [fid for fid, n in stats.items() if n == 0]
    print(f"Files with zero facts: {zero}")
    by_cat = Counter(f.category for f in store.facts if not f.is_claim)
    for cat, n in by_cat.most_common():
        print(f"  {cat:24s} {n}")
    shown = Counter()
    for fact in store.facts:
        key = fact.source_id.rsplit("_", 1)[0]
        if shown[fact.category] < 1 and not fact.is_claim:
            print("EXAMPLE", fact)
            shown[fact.category] += 1
    print("PASS" if not zero else "CHECK zero-fact files above")


if __name__ == "__main__":
    main()
