"""Entry point: python3 code/main.py [--input eval|sample] [--limit N] [--no-cache] [--offline]

Reads dataset/, writes output.csv at the repository root (or --output),
plus cache/review.jsonl, cache/usage.json and cache/run.log.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ghost.config import OUTPUT_CSV, REQUESTS_CSV, SAMPLE_REQUESTS_CSV, Settings  # noqa: E402
from ghost.dataset_io import load_requests  # noqa: E402
from ghost.errors import GhostError  # noqa: E402
from ghost.logging_setup import setup_logging  # noqa: E402
from ghost.run import build_context, run_all, write_all  # noqa: E402

log = logging.getLogger("ghost.main")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ghost Data Still Exists deletion audit")
    p.add_argument("--input", choices=("eval", "sample"), default="eval",
                   help="eval = deletion_requests.csv (default), sample = the 32 labeled samples")
    p.add_argument("--output", type=Path, default=None, help="output CSV path")
    p.add_argument("--limit", type=int, default=None, help="process only the first N cases")
    p.add_argument("--no-cache", action="store_true", help="rebuild startup tables")
    p.add_argument("--offline", action="store_true", help="never call the model API")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging on console")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)
    settings = Settings.from_env(offline=args.offline)
    log.info("model=%s offline=%s", settings.model, settings.offline)

    source = SAMPLE_REQUESTS_CSV if args.input == "sample" else REQUESTS_CSV
    output = args.output or (OUTPUT_CSV if args.input == "eval" else None)
    if output is None:
        from ghost.config import CACHE_DIR
        output = CACHE_DIR / "sample_predictions.csv"

    try:
        requests = load_requests(source)
        if args.limit is not None:
            requests = requests[: args.limit]
        ctx = build_context(settings, use_cache=not args.no_cache)
        results = run_all(requests, ctx)
        write_all(results, output)
    except GhostError as exc:
        log.error("run failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
