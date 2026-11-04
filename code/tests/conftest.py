from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "dataset"


@pytest.fixture(scope="session")
def dataset_dir() -> Path:
    return DATASET_DIR


@pytest.fixture(scope="session")
def scanner(dataset_dir):
    from evidence import EvidenceScanner

    s = EvidenceScanner(dataset_dir)
    s.load()
    return s
