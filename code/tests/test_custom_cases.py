import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.custom_cases import run_all    # noqa: E402


@pytest.fixture(scope="module")
def outcomes(ec):
    return run_all(ec)


def test_all_custom_cases_pass(outcomes):
    failed = [(c.name, detail) for c, ok, detail in outcomes if not ok]
    assert failed == []


def test_there_are_at_least_three_custom_cases(outcomes):
    assert len(outcomes) >= 3
