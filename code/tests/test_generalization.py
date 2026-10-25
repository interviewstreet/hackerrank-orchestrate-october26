"""Generalization guard: decision code holds no case ids, resource ids or request texts.

Decision code is every ``.py`` file under ``code/`` except ``tests/``, ``evaluation/`` and
``llm_snapshot.py`` (validated model output), plus the prompts. Every string literal is
scanned, docstrings included. Any hit fails the test.
"""

import ast
import csv
import re
import unittest
from pathlib import Path

import helpers
import policy
from loaders import DATASET_DIR, Rule, load_rules

CODE_DIR = helpers.CODE_DIR
EXCLUDED = ("tests/", "evaluation/")
RE_ID_LITERAL = re.compile(r"^[a-z_]+_\d+$")          # a whole literal shaped like a resource id
RE_ID_TOKEN = re.compile(r"\b[a-z]+(?:_[a-z]+)*_\d+\b")
RE_CASE = re.compile(r"\bcase_\d+\b")
MIN_TEXT = 20   # shorter literals are generic phrases ("delete my account")


def decision_files() -> list[Path]:
    files = []
    for path in sorted(CODE_DIR.rglob("*.py")):
        rel = path.relative_to(CODE_DIR).as_posix()
        if not rel.startswith(EXCLUDED) and rel != "llm_snapshot.py" and "__pycache__" not in rel:
            files.append(path)
    return files


def literals(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def norm(text: str) -> str:
    return " ".join(text.lower().split())


def request_texts() -> list[str]:
    texts = []
    for name in ("sample_deletion_requests.csv", "deletion_requests.csv"):
        with open(DATASET_DIR / name, encoding="utf-8-sig", newline="") as handle:
            texts += [norm(r["request_text"]) for r in csv.DictReader(handle)]
    return [t for t in texts if len(t) >= MIN_TEXT]


def dataset_ids() -> set[str]:
    """Every id-shaped token in the participant tables (case, user, resource, evidence, audit ids)."""
    ids: set[str] = set()
    for path in DATASET_DIR.glob("*.csv"):
        ids.update(RE_ID_TOKEN.findall(path.read_text(encoding="utf-8-sig")))
    return ids


class LiteralScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = request_texts()
        cls.blob = "\n".join(cls.texts)
        cls.ids = dataset_ids()
        cls.sources = [(p.relative_to(CODE_DIR).as_posix(), literals(p)) for p in decision_files()]
        cls.prompts = [(p.relative_to(CODE_DIR).as_posix(), p.read_text(encoding="utf-8"))
                       for p in sorted((CODE_DIR / "prompts").glob("*.md"))]

    def test_scan_covers_the_decision_modules(self):
        names = {rel for rel, _ in self.sources}
        self.assertTrue({"main.py", "policy.py", "links.py", "planner.py", "intent.py",
                         "evidence/extract_vision.py", "agent/loop.py"} <= names)
        self.assertNotIn("llm_snapshot.py", names)

    def test_no_case_or_resource_id_literals(self):
        hits = []
        for rel, lits in self.sources:
            for line, value in lits:
                if RE_ID_LITERAL.match(value) or RE_CASE.search(value):
                    hits.append(f"{rel}:{line} {value[:60]!r}")
                elif known := sorted(set(RE_ID_TOKEN.findall(value)) & self.ids):
                    hits.append(f"{rel}:{line} dataset id {known[:3]}")
        self.assertEqual(hits, [])

    def test_no_request_text_in_decision_code(self):
        hits = []
        for rel, lits in self.sources:
            for line, value in lits:
                v = norm(value)
                if (len(v) >= MIN_TEXT and v in self.blob) or any(t in v for t in self.texts):
                    hits.append(f"{rel}:{line} {v[:60]!r}")
        self.assertEqual(hits, [])

    def test_prompts_hold_no_case_ids_dataset_ids_or_request_texts(self):
        hits = []
        for rel, text in self.prompts:
            if RE_CASE.search(text):
                hits.append(f"{rel}: case id")
            if known := sorted(set(RE_ID_TOKEN.findall(text)) & self.ids):
                hits.append(f"{rel}: dataset ids {known[:3]}")
            flat = norm(text)
            hits += [f"{rel}: request text {t[:40]!r}" for t in self.texts if t in flat]
        self.assertEqual(hits, [])

    def test_scanner_catches_a_planted_label(self):
        planted = 'LABELS = {"case_17": "COMPLETE", "x": "account_5762"}\n'
        tree = ast.parse(planted)
        values = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertTrue(any(RE_CASE.search(v) for v in values))
        self.assertTrue(any(RE_ID_LITERAL.match(v) for v in values))


class RuleBindingTest(unittest.TestCase):
    """Rule ids and actions come from deletion_rules.csv, never from literals in code."""

    def test_rules_match_the_rule_file(self):
        rules = load_rules(DATASET_DIR / "deletion_rules.csv")
        self.assertEqual({r.data_category: r.rule_id for r in rules},
                         {c: v[0] for c, v in policy.RULES.items() if c != "DATA_FLOW"})

    def test_an_action_that_the_treatment_cannot_carry_out_stops_the_run(self):
        with self.assertRaises(ValueError):
            policy.bind_rules([Rule("r1", "USER_PROFILE", "Always", "RETAIN")])
        with self.assertRaises(ValueError):
            policy.bind_rules([Rule("r1", "UNKNOWN_CATEGORY", "Always", "DELETE")])


if __name__ == "__main__":
    unittest.main()
