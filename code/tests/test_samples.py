import unittest

from code.preflight import run_preflight


class SubmissionArtifactTests(unittest.TestCase):
    def test_repository_preflight_blocks_missing_release_output(self):
        errors = run_preflight(".", require_package=False)
        self.assertIn("output.csv is missing", errors)
