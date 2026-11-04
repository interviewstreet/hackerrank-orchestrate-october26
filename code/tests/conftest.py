import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from engine.case_analyzer import build_context   # noqa: E402


@pytest.fixture(scope="session")
def ec():
    return build_context(ROOT / "dataset")


@pytest.fixture(scope="session")
def root():
    return ROOT
