#!/usr/bin/env python3
"""Identity test: every request resolves; current vs historical split."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.config import DEFAULT_DATASET_DIR              # noqa: E402
from audit.identity import IdentityResolver               # noqa: E402
from audit.loaders import load_dataset                    # noqa: E402


def main():
    data = load_dataset(DEFAULT_DATASET_DIR)
    resolver = IdentityResolver(data["identities"], data["audit_log"])
    current = {r["email"].strip().lower(): r["user_id"]
               for r in data["identities"]}
    resolved = current_n = historical_n = 0
    for req in data["requests"]:
        uid = resolver.resolve(req["email"])
        assert uid, f"unresolved: {req['case_id']}"
        resolved += 1
        if current.get(req["email"].strip().lower()) == uid:
            current_n += 1
        else:
            historical_n += 1
    print(f"Resolved {resolved}/518 requests "
          f"(current={current_n}, historical={historical_n})")
    assert resolved == 518
    print("PASS")


if __name__ == "__main__":
    main()
