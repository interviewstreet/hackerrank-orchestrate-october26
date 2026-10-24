"""Public-sample regression runner with case, step, field, and sequence metrics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from code.ingest import load_all
from code.main import run_pipeline

FIELDS = ("phase", "operation", "state", "system_id", "resource_id", "evidence_id")


def run_evaluation(repo_root):
    data = load_all(repo_root)
    actual = {row["case_id"]: row for row in run_pipeline(repo_root, sample=True)}
    truth = data["sample_output"]
    status_correct = step_correct = total_steps = sequence_correct = 0
    field_correct = field_total = count_correct = 0
    breakdown = []
    for case_id in sorted(truth):
        expected, got = truth[case_id], actual.get(case_id, {})
        expected_steps = json.loads(expected["steps_json"])
        actual_steps = json.loads(got.get("steps_json", "[]"))
        status_ok = got.get("deletion_status") == expected["deletion_status"]
        status_correct += status_ok
        count_correct += len(expected_steps) == len(actual_steps)
        total_steps += len(expected_steps)
        positional = 0
        mismatches = []
        if not status_ok:
            mismatches.append(f"status expected={expected['deletion_status']} actual={got.get('deletion_status')}")
        if len(expected_steps) != len(actual_steps):
            mismatches.append(f"step_count expected={len(expected_steps)} actual={len(actual_steps)}")
        for index, (expected_step, actual_step) in enumerate(zip(expected_steps, actual_steps), 1):
            bad = [field for field in FIELDS if expected_step.get(field) != actual_step.get(field)]
            field_correct += len(FIELDS) - len(bad)
            field_total += len(FIELDS)
            if not bad:
                positional += 1
            else:
                mismatches.append(f"step {index} fields={','.join(bad)}")
        # Missing expected positions count as incorrect for every compared field.
        field_total += max(0, len(expected_steps) - len(actual_steps)) * len(FIELDS)
        step_correct += positional
        sequence_ok = status_ok and len(expected_steps) == len(actual_steps) and positional == len(expected_steps)
        sequence_correct += sequence_ok
        breakdown.append((case_id, "PASS" if sequence_ok else "FAIL", mismatches))

    case_count = len(truth)
    print("=== Sample Evaluation Report ===")
    print(f"Case-level status accuracy: {status_correct} of {case_count} correct ({status_correct/case_count:.1%})")
    print(f"Step-count accuracy: {count_correct} of {case_count} cases ({count_correct/case_count:.1%})")
    print(f"Step-level accuracy: {step_correct} / {total_steps} ({step_correct/total_steps:.1%})")
    print(f"Field-level accuracy: {field_correct} / {field_total} ({field_correct/field_total:.1%})")
    print(f"Sequence accuracy: {sequence_correct} of {case_count} cases ({sequence_correct/case_count:.1%})")
    print("--- Per-case breakdown ---")
    for case_id, result, mismatches in breakdown:
        print(f"{case_id}: {result}" + (f" | {'; '.join(mismatches)}" if mismatches else ""))
    return {"status_correct": status_correct, "step_count_correct": count_correct,
            "step_correct": step_correct, "total_steps": total_steps,
            "field_correct": field_correct, "field_total": field_total,
            "sequence_correct": sequence_correct}


def main():
    run_evaluation(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
