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


class TestReviewFindings(unittest.TestCase):
    """The 4 sentences the code review found misclassified."""

    def test_do_not_hesitate_is_deletion(self):
        r = classify_request("Please do not hesitate to delete everything you hold about me.")
        self.assertEqual(r.label, IS_DEL)

    def test_not_been_erased_complaint_is_deletion(self):
        self.assertEqual(classify_request("My profile has still not been erased.").label, IS_DEL)

    def test_exclude_me_from_marketing_is_opt_out(self):
        self.assertEqual(classify_request("Please exclude me from your marketing emails.").label, NA)

    def test_remove_my_email_from_list_is_opt_out(self):
        self.assertEqual(classify_request("Please remove my email from your marketing list.").label, NA)


class TestNegationMustBeInstruction(unittest.TestCase):
    """A negated *description* is not a refusal; a negated *instruction* is."""

    DESCRIPTIONS_ARE_DELETION = [
        "You marked my request complete, but my data was not removed. Please remove it.",
        "Mi cuenta no fue eliminada todavía.",
        "Le compte n'a pas été supprimé, merci de le supprimer.",
        "Minha conta ainda não foi excluída, por favor excluam.",
        "データがまだ削除されていません。",
        "제 계정이 아직 삭제되지 않았습니다.",
        # "remove my email from" something that is not a list = deletion
        "Please remove my email from your systems.",
    ]
    INSTRUCTIONS_ARE_NOT_APPLICABLE = [
        "I don't want my account deleted, just unsubscribe me.",
        "Please don’t delete my account, I only need a copy of my invoices.",
        "No quiero eliminar mi cuenta, solo cambiar mi correo.",
        "Ne pas supprimer mon compte, je veux juste corriger mon adresse.",
    ]

    def test_descriptions(self):
        for text in self.DESCRIPTIONS_ARE_DELETION:
            with self.subTest(text=text):
                self.assertEqual(classify_request(text).label, IS_DEL)

    def test_instructions(self):
        for text in self.INSTRUCTIONS_ARE_NOT_APPLICABLE:
            with self.subTest(text=text):
                self.assertEqual(classify_request(text).label, NA)


class TestOrStartsNewRequest(unittest.TestCase):
    """'or' joins two separate requests, like 'and' / 'but' (review fix)."""

    CASES = [
        "Delete my account or update my email.",                       # EN
        "Eliminen mi cuenta o cambien mi correo.",                     # ES
        "Excluam minha conta ou alterem meu e-mail.",                  # PT
        "Supprimez mon compte ou modifiez mon adresse.",               # FR
        "アカウントを削除またはメールアドレスを変更してください。",          # JA
        "계정을 삭제 또는 이메일 주소를 변경해 주세요.",                    # KO
    ]

    def test_or_gives_uncertain(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(classify_request(text).label, UNC)

    def test_object_of_deletion_still_works(self):
        """Without a conjunction, the word after the verb is still the object."""
        self.assertEqual(
            classify_request("Eliminen cualquier copia de mis datos.").label, IS_DEL)


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
