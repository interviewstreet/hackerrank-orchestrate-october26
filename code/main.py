#!/usr/bin/env python3
"""Ghost Data Still Exists -- deletion audit agent (entry point).

Usage:
  python3 code/main.py                      # full run -> ./output.csv
  python3 code/main.py --no-llm             # deterministic, no LLM calls
  python3 code/main.py --sample             # sample cases -> evaluation file
  python3 code/main.py --cases case_05,case_06 --debug
Reads only ./dataset/, writes output.csv at the repository root.
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit import activity as activity_mod          # noqa: E402
from audit.config import DEFAULT_DATASET_DIR, DEFAULT_OUT, EVALUATION_DIR  # noqa: E402
from audit.identity import IdentityResolver         # noqa: E402
from audit.intent import classify_texts             # noqa: E402
from audit.loaders import case_sort_key, load_dataset, parse_ts  # noqa: E402
from audit.parsers import build_fact_store          # noqa: E402
from audit.planner import build_steps               # noqa: E402
from audit.policy import RuleBook                   # noqa: E402
from audit.state import StateReconstructor          # noqa: E402
from audit.writer import validate, write_output     # noqa: E402


def run(dataset_dir, out_path, use_llm, only_cases=None, debug=False,
        requests_file="deletion_requests.csv"):
    data = load_dataset(dataset_dir, requests_file)
    requests = sorted(data["requests"], key=lambda r: case_sort_key(r["case_id"]))
    if only_cases:
        wanted = set(only_cases)
        requests = [r for r in requests if r["case_id"] in wanted]

    resolver = IdentityResolver(data["identities"], data["audit_log"])
    rulebook = RuleBook(data["rules"])
    store, parse_stats = build_fact_store(dataset_dir, data["evidence_files"])
    links, classify_events = activity_mod.load_activity(store, data["activity"])

    unique_texts = sorted({r["request_text"] for r in data["requests"]} |
                          {r["request_text"] for r in requests})
    intents = classify_texts(unique_texts, use_llm=use_llm)
    if debug:
        non_delete = [t for t, v in intents.items() if v["intent"] != "DELETE"]
        print(f"[intent] {len(intents)} unique texts, "
              f"{len(non_delete)} NON_DELETE")
        for t in non_delete:
            print(f"  NON_DELETE: {t[:120]!r}")

    reconstructor = StateReconstructor(store, rulebook)
    rows = []
    counts = collections.Counter()
    for i, req in enumerate(requests, start=1):
        try:
            status, steps = _audit_case(req, resolver, reconstructor, links,
                                        intents, debug)
        except Exception as exc:  # never drop a row
            print(f"WARNING: {req['case_id']} failed ({exc}); emitting fallback")
            status, steps = "INCOMPLETE", []
        rows.append((req["case_id"], status, steps))
        counts[status] += 1
        if i % 50 == 0:
            print(f"  ... {i}/{len(requests)} cases")

    evidence_ids = {r["file_id"] for r in data["evidence_files"]}
    activity_ids = {r["activity_id"] for r in data["activity"]}
    audit_ids = {r["audit_id"] for r in data["audit_log"]}
    write_output(rows, out_path)
    # Validation is contract-level on the full requested row set.
    full_requests = data["requests"] if not only_cases else requests
    if not only_cases or len(rows) == len(full_requests):
        try:
            validate(rows, full_requests, evidence_ids, activity_ids, audit_ids)
            print("Validation: OK")
        except ValueError as exc:
            print(str(exc))
            if not only_cases and requests_file == "deletion_requests.csv":
                raise
    print(f"Wrote {out_path} ({len(rows)} rows) | "
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return rows


def _audit_case(req, resolver, reconstructor, links, intents, debug):
    intent = intents.get(req["request_text"], {}).get("intent", "DELETE")
    if intent != "DELETE":
        return "NOT_APPLICABLE", []
    audit_at = parse_ts(req["audit_at"])
    user_id = resolver.resolve(req["email"])
    if user_id is None:  # fall back to searching by the raw email only
        ids = {"emails": {req["email"].strip().lower()}, "hashes": set(),
               "phones": set(), "user_ids": set(), "name": ""}
    else:
        ids = resolver.identifiers(user_id)
    states = reconstructor.evaluate_case(ids, audit_at, links)
    status, steps = build_steps("DELETE", states)
    if debug:
        print(f"\n{req['case_id']} user={user_id} audit={req['audit_at']} "
              f"-> {status}")
        for s in states:
            print(f"  {s.system_id:20s} {s.resource_id:20s} {s.category:22s} "
                  f"{s.verdict} ev={s.evidence_id}")
    return status, steps


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deletion audit agent")
    ap.add_argument("--no-llm", action="store_true",
                    help="rule-based intent only (no LLM calls)")
    ap.add_argument("--cases", default="", help="comma-separated case ids")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    ap.add_argument("--out", default=None)
    ap.add_argument("--sample", action="store_true",
                    help="run sample_deletion_requests.csv instead")
    args = ap.parse_args(argv)

    dataset_dir = Path(args.dataset_dir)
    if args.sample:
        out = Path(args.out) if args.out else \
            (EVALUATION_DIR / "sample_predictions.csv")
        return run(dataset_dir, out, use_llm=not args.no_llm,
                   only_cases=args.cases.split(",") if args.cases else None,
                   debug=args.debug,
                   requests_file="sample_deletion_requests.csv")
    out = Path(args.out) if args.out else DEFAULT_OUT
    return run(dataset_dir, out, use_llm=not args.no_llm,
               only_cases=args.cases.split(",") if args.cases else None,
               debug=args.debug)


if __name__ == "__main__":
    main()
