"""
test_request_classifier.py — tests for classify_request().

Run from the repo root with:
    python3 code/test_request_classifier.py
or:
    python3 -m pytest code/test_request_classifier.py -v
"""
from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from models import ClassificationResult
from request_classifier import classify_request

IS_DEL = ClassificationResult.IS_DELETION
NA = ClassificationResult.NOT_APPLICABLE
UNC = ClassificationResult.UNCERTAIN

DATASET_DIR = Path(__file__).parent.parent / "dataset"
REQ_PATH = DATASET_DIR / "deletion_requests.csv"
SAMPLE_PATH = DATASET_DIR / "sample_deletion_requests.csv"


def _load(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Made-up sentences that are NOT in the dataset — prove the rules are general
# ---------------------------------------------------------------------------

class TestMadeUpNotApplicable(unittest.TestCase):
    CASES = [
        "Don't erase my account, I just want my address updated",
        "No eliminen mi cuenta, solo quiero una copia de mis datos.",
        "Ne supprimez pas mon compte, je veux seulement corriger mon nom.",
        "Não exclua minha conta, quero apenas atualizar meu telefone.",
        "アカウントを削除しないでください。パスワードを再設定したいです。",
        "계정을 삭제하지 마세요. 마케팅 이메일 수신 거부만 원합니다.",
        "Please unsubscribe me from your newsletter, I want to keep my account.",
        "Remove me from the mailing list, please.",
        "Could you send me a copy of my order history?",
    ]

    def test_not_applicable(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(classify_request(text).label, NA)


class TestMadeUpDeletion(unittest.TestCase):
    CASES = [
        "Supprimez mon compte définitivement.",
        "アカウントを削除してください",
        "Por favor, borren todos mis datos personales y cierren la cuenta.",
        "Quero que apaguem a minha conta e todos os dados.",
        "제 계정을 탈퇴 처리하고 개인정보를 삭제해 주세요.",
        # tricky: negation that is not about deletion
        "Please delete my account. Do not keep any backups of my data.",
        # tricky: "not" in a separate sentence from "delete"
        "I do not want this account anymore. Please delete it.",
        # tricky: "copies" is the thing to delete, not a request for a copy
        "Please remove any remaining copies of my profile from your systems.",
    ]

    def test_is_deletion(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(classify_request(text).label, IS_DEL)


class TestMadeUpUncertain(unittest.TestCase):
    CASES = [
        # deletion + negation of a different deletion
        "Don't close my account, but delete my old order history.",
        "Eliminen mi cuenta pero no borren mis facturas.",
        # deletion + separate non-deletion request
        "Delete my account and send me a copy of my data first.",
        # nothing matches
        "What is the weather like today?",
        "",
    ]

    def test_uncertain(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(classify_request(text).label, UNC)


class TestResultShape(unittest.TestCase):
    def test_returns_classification_result(self):
        r = classify_request("Please delete my account.")
        self.assertIsInstance(r, ClassificationResult)
        self.assertTrue(r.is_deletion())
        self.assertEqual(r.confidence, "HIGH")
        self.assertIn("DELETION:delete", r.matched_keywords)

    def test_uncertain_is_low_confidence(self):
        self.assertEqual(classify_request("Hello there.").confidence, "LOW")

    def test_curly_apostrophe_negation(self):
        r = classify_request("Please don’t delete my account.")
        self.assertEqual(r.label, NA)

    def test_deterministic(self):
        t = "Please stop the promotional emails. I am not asking for deletion."
        a, b = classify_request(t), classify_request(t)
        self.assertEqual((a.label, a.matched_keywords), (b.label, b.matched_keywords))


# ---------------------------------------------------------------------------
# Real dataset
# ---------------------------------------------------------------------------

EXPECTED_NA = {f"case_{n}" for n in range(533, 543)}


@unittest.skipUnless(REQ_PATH.exists(), "Real dataset not present")
class TestRealDataset(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.requests = _load(REQ_PATH)
        cls.results = {r["case_id"]: classify_request(r["request_text"]) for r in cls.requests}

    def test_518_requests(self):
        self.assertEqual(len(self.results), 518)

    def test_no_uncertain(self):
        unc = sorted(c for c, r in self.results.items() if r.label == UNC)
        self.assertEqual(unc, [])

    def test_exactly_533_to_542_not_applicable(self):
        na = {c for c, r in self.results.items() if r.label == NA}
        self.assertEqual(na, EXPECTED_NA)

    def test_everything_else_is_deletion(self):
        for c, r in self.results.items():
            if c not in EXPECTED_NA:
                with self.subTest(case=c):
                    self.assertEqual(r.label, IS_DEL)


@unittest.skipUnless(SAMPLE_PATH.exists(), "Sample dataset not present")
class TestSampleDataset(unittest.TestCase):

    def test_all_32_samples_are_deletion(self):
        rows = _load(SAMPLE_PATH)
        self.assertEqual(len(rows), 32)
        for r in rows:
            with self.subTest(case=r["case_id"]):
                self.assertEqual(classify_request(r["request_text"]).label, IS_DEL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
