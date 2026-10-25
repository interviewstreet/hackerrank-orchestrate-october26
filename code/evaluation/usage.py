"""Print the usage tables for usage_report.md from code/cache/usage_log.jsonl (token counts of real API calls).

    python code/evaluation/usage.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from audit.llm import PRICES, USAGE_FILE, cost  # noqa: E402

N_CASES = 518


def main():
    calls = [json.loads(line) for line in USAGE_FILE.read_text().splitlines() if line.strip()] \
        if USAGE_FILE.exists() else []
    by = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0})
    for c in calls:
        for k in ((c["model"], c["purpose"]), (c["model"], "all")):
            by[k]["calls"] += 1
            by[k]["in"] += c["input_tokens"]
            by[k]["out"] += c["output_tokens"]
    total_in = sum(c["input_tokens"] for c in calls)
    total_out = sum(c["output_tokens"] for c in calls)
    total_cost = sum(cost(c["model"], c["input_tokens"], c["output_tokens"]) for c in calls)
    lines = ["| Provider | Model | Purpose | Calls | Input tokens | Output tokens | Avg tokens / call | Cost (USD) |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for (model, purpose), v in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1] == "all", kv[0][1])):
        avg = (v["in"] + v["out"]) / v["calls"] if v["calls"] else 0
        lines.append(f"| Anthropic | `{model}` | {purpose if purpose != 'all' else '**model total**'} | {v['calls']} | "
                     f"{v['in']:,} | {v['out']:,} | {avg:,.0f} | {cost(model, v['in'], v['out']):.4f} |")
    n = len(calls)
    summary = {
        "calls": n, "in": total_in, "out": total_out, "cost": total_cost,
        "avg_call": (total_in + total_out) / n if n else 0,
        "per_case_tokens": (total_in + total_out) / N_CASES,
        "per_case_cost": total_cost / N_CASES,
    }
    prices = "\n".join(f"- `{m}`: ${pin:.2f} input / ${pout:.2f} output per million tokens"
                       for m, (pin, pout) in PRICES.items())
    print("\n".join(lines))
    print(json.dumps(summary, indent=1))
    print(prices)


if __name__ == "__main__":
    main()
