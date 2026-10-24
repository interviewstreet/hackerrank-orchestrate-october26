import unittest

from code.preflight import run_preflight


class SubmissionArtifactTests(unittest.TestCase):
    def test_repository_preflight_without_optional_package(self):
        self.assertEqual(run_preflight(".", require_package=False), [])
