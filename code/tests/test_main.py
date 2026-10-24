import unittest

from code.main import run_pipeline


class MainCliTests(unittest.TestCase):
    def test_unknown_partial_case_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown case_id"):
            run_pipeline(".", cases=["case_does_not_exist"])

    def test_known_sample_case_can_be_selected_for_smoke_test(self):
        rows = run_pipeline(".", cases=["case_01"])
        self.assertEqual([row["case_id"] for row in rows], ["case_01"])
