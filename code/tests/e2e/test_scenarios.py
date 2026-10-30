"""Runs every scenario through `main.py` as a subprocess (the real entry point) and diffs the output rows."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .scenarios import SCENARIOS

MAIN = Path(__file__).resolve().parents[2] / "main.py"


def run_scenario(fn, workdir: Path) -> tuple[dict, dict, str]:
    ds, expected = fn()
    root = ds.write(workdir / "dataset")
    out = workdir / "output.csv"
    env = dict(os.environ, GDA_LLM_BACKEND="offline", GDA_BUDGET_USD="0")
    proc = subprocess.run([sys.executable, str(MAIN), "--dataset-dir", str(root), "--out", str(out),
                           "--trace-dir", str(workdir / "trace"), "--backend", "offline"],
                          capture_output=True, text=True, env=env, cwd=workdir)
    got = {}
    if out.exists():
        with open(out, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                steps = [tuple(s[k] for k in ("phase", "system_id", "resource_id", "operation", "state", "evidence_id"))
                         for s in json.loads(r["steps_json"])]
                got[r["case_id"]] = (r["deletion_status"], steps)
    return expected, got, proc.stdout + proc.stderr


class ScenarioTests(unittest.TestCase):
    pass


def _make(fn):
    def test(self):
        with tempfile.TemporaryDirectory(prefix="gda_e2e_") as tmp:
            expected, got, log = run_scenario(fn, Path(tmp))
            for cid, (status, steps) in expected.items():
                self.assertIn(cid, got, f"{cid} missing from output\n{log}")
                self.assertEqual(got[cid][0], status, f"{cid} status\n{log}")
                self.assertEqual(got[cid][1], steps, f"{cid} steps")
    test.__doc__ = fn.__doc__ or fn.__name__
    return test


for _fn in SCENARIOS:
    setattr(ScenarioTests, f"test_{_fn.__name__}", _make(_fn))


if __name__ == "__main__":
    unittest.main()
