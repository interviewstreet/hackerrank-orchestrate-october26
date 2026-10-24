"""Frozen custom cases and metamorphic checks (code/evaluation). No network."""

import importlib.util
import sys
import unittest

import config
import helpers  # noqa: F401
from schema import OutputRow

if str(config.CODE_DIR / "evaluation") not in sys.path:
    sys.path.append(str(config.CODE_DIR / "evaluation"))  # after code/: never shadow main
import custom
import metamorphic

REQUIRED = {"name", "purpose", "rule", "request", "identities", "audit_log", "activity", "evidence",
            "agent_replies", "expected"}


class CustomCaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = custom.load_cases()

    def test_cases_are_well_formed(self):
        self.assertGreaterEqual(len(self.cases), 6)
        ids = [c["request"]["case_id"] for c in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.cases:
            with self.subTest(case["name"]):
                self.assertEqual(REQUIRED - set(case), set())
                want = case["expected"]
                OutputRow(case_id=case["request"]["case_id"], deletion_status=want["deletion_status"],
                          steps=want["steps"])

    def test_every_custom_case_passes(self):
        for case in self.cases:
            with self.subTest(case["name"]):
                result = custom.check(case)
                self.assertEqual(result["problems"], [])


class MetamorphicTest(unittest.TestCase):
    def test_every_metamorphic_check_passes(self):
        for check in metamorphic.all_checks():
            with self.subTest(check["name"]):
                self.assertTrue(check["passed"], check["detail"])


class ScorerTest(unittest.TestCase):
    def test_shifted_step_is_a_content_match_but_not_an_exact_match(self):
        spec = importlib.util.spec_from_file_location("eval_main", config.CODE_DIR / "evaluation" / "main.py")
        scorer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scorer)

        def step(n, rid):
            return {"step_no": n, "phase": "VERIFICATION", "system_id": "s", "resource_id": rid,
                    "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT", "evidence_id": "e"}

        gold = {"case_1": ("COMPLETE", [step(1, "a"), step(2, "b")])}
        pred = {"case_1": ("COMPLETE", [step(1, "b")])}   # "a" is missing, so "b" moves to step 1
        steps = scorer.score(gold, pred)["steps"]
        self.assertEqual((steps["exact"]["matched"], steps["content"]["matched"]), (0, 1))
        self.assertEqual(steps["content"]["precision"], 1.0)
        self.assertEqual(steps["exact"]["precision"], 0.0)


if __name__ == "__main__":
    unittest.main()
