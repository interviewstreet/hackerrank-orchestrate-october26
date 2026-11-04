"""Write plain-language explanations and review flags to explanations.json (never touches output.csv).

    python code/advise.py                 # templates only, no model calls, no key needed
    python code/advise.py --model         # model second opinion on flagged cases (needs ANTHROPIC_API_KEY in the environment)
    python code/advise.py --model --limit 20
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from advisor.advisor import advise_all                     # noqa: E402
from advisor.llm_client import AnthropicClient             # noqa: E402
from engine.case_analyzer import build_context             # noqa: E402


def main() -> int:
    root = HERE.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default=str(root / "dataset"))
    ap.add_argument("--out", default=str(root / "explanations.json"))
    ap.add_argument("--usage-out", default=str(root / "code" / "evaluation" / "advisor_usage.json"))
    ap.add_argument("--model", action="store_true", help="use the language model on flagged cases")
    ap.add_argument("--limit", type=int, default=None, help="maximum number of model calls")
    a = ap.parse_args()

    ec = build_context(a.dataset)
    client = AnthropicClient() if a.model else None
    if a.model and not client.available:
        print("ANTHROPIC_API_KEY is not set: continuing with template explanations only.")
    advice = advise_all(ec.ctx.requests, ec, client, a.limit)
    Path(a.out).write_text(json.dumps(advice, indent=1, ensure_ascii=False), encoding="utf-8")
    flagged = sum(x["review_needed"] for x in advice)
    used = sum(x["source"] == "model" for x in advice)
    print(f"wrote {a.out}: {len(advice)} cases, {flagged} flagged for review, {used} explained by the model")
    if client is not None and client.usage.calls + client.usage.failed_calls:
        Path(a.usage_out).write_text(json.dumps(client.usage.to_dict(), indent=1), encoding="utf-8")
        print(f"model usage: {client.usage.calls} calls, {client.usage.input_tokens} in / {client.usage.output_tokens} out tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
