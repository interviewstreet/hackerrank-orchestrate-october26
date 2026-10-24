import unittest

import helpers  # noqa: F401  (sets sys.path)
from intent import AMBIGUOUS, DELETE, NOT_DELETION, VERIFY_DELETE, classify, split_clauses, treat_as_deletion


class IntentTest(unittest.TestCase):
    def assertLabel(self, text, label):
        result = classify(text)
        self.assertEqual(result.label, label, f"{text!r} -> {result.label} {result.reasons}")
        return result

    def test_plain_deletion(self):
        for text in (
            "Please permanently delete the account associated with this email address.",
            "I would like the account associated with this address to be erased.",
            "I no longer use this account and would like it permanently deleted.",
            "Hi, I haven't used this account in years and would like it closed.",
            "Close the account completely and make sure it can no longer send my data to other systems.",
            "I'm deleting my account. You can keep anonymous statistics, but nothing should point back to me.",
        ):
            self.assertLabel(text, DELETE)

    def test_multilingual_deletion(self):
        for text in (
            "Solicito la eliminación permanente de la cuenta asociada a este correo.",
            "Solicito a exclusão permanente da conta associada a este e-mail.",
            "Je demande la suppression définitive du compte associé à cette adresse e-mail.",
            "このメールアドレスに関連するアカウントの完全な削除を依頼します。",
            "이 이메일 주소에 연결된 계정의 영구 삭제를 요청합니다.",
            "Bitte löschen Sie mein Konto.",
        ):
            self.assertLabel(text, DELETE)

    def test_negation_is_clause_level(self):
        for text in (
            "I still need the account, so I am not asking for deletion.",
            "I still use it, so please don't delete or change anything.",
            "Do not close the account.",
            "Can you correct my surname without removing any of my records?",
            "This is an information request, not a request to erase it.",
            "Please never erase my profile.",
        ):
            result = self.assertLabel(text, NOT_DELETION)
            self.assertIn("negated", result.reasons)

    def test_no_longer_is_not_negation(self):
        self.assertLabel("I no longer need this account. Please remove my name and contact details.", DELETE)

    def test_negation_in_other_clause_does_not_cancel(self):
        # The negated clause is about a record, not about deletion.
        self.assertLabel("Please delete my account. Systems that do not display the email count too.", DELETE)

    def test_other_requests_are_not_deletion(self):
        for text in (
            "Please change the email address used for this account. I want to continue using the service.",
            "I'd like to download my account information in a portable format. Please keep the account as it is.",
            "Please remove me from marketing lists only. I still want receipts for this account.",
            "Please stop the promotional emails.",
            "I need a copy of last year's invoices for my records.",
        ):
            self.assertLabel(text, NOT_DELETION)

    def test_verify_requests_count_as_deletion(self):
        for text in (
            "Can you verify that my account was deleted?",
            "Please audit the deletion as it stood when my request was reviewed.",
            "Please inspect the systems and tell me whether the account data have already been removed.",
            "Please check that nothing tied to the old address was left behind.",
        ):
            result = self.assertLabel(text, VERIFY_DELETE)
            self.assertTrue(result.is_deletion)

    def test_verify_with_action_is_delete(self):
        self.assertLabel("¿Pueden comprobar si queda algún dato y completar la eliminación si hace falta?", DELETE)

    def test_remnant_after_past_deletion_is_delete(self):
        self.assertLabel("I was told the account had been deleted, but I can still find traces in search. "
                         "Please handle them.", DELETE)

    def test_conflicting_signals_are_ambiguous(self):
        result = self.assertLabel("Please delete my account. Please keep the account as it is.", AMBIGUOUS)
        self.assertTrue(result.flagged)
        self.assertTrue(treat_as_deletion(result))  # phase 1 policy

    def test_no_signal_is_ambiguous(self):
        result = self.assertLabel("Hello, I have a question about my order.", AMBIGUOUS)
        self.assertIn("no_signal", result.reasons)

    def test_split_clauses(self):
        self.assertEqual(split_clauses("I still need it, so I am not asking for deletion."),
                         ["I still need it", "I am not asking for deletion"])


if __name__ == "__main__":
    unittest.main()
