import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.case_analyzer import build_context   # noqa: E402


@pytest.fixture(scope="session")
def ec():
    if not (ROOT / "dataset" / "deletion_requests.csv").exists():
        pytest.skip("real dataset/ not present (the mini-dataset and unit tests still run)")
    return build_context(ROOT / "dataset")


@pytest.fixture(scope="session")
def root():
    if not (ROOT / "dataset" / "deletion_requests.csv").exists() or not (ROOT / "output.csv").exists():
        pytest.skip("real dataset/ or output.csv not present")
    return ROOT
