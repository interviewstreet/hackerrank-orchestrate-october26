"""End-to-end evaluation on a tiny self-contained dataset with hand-derived answers."""
import pytest

from engine.case_analyzer import analyze_case, build_context
from minidata import EXPECTED, build_mini_dataset


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    d = build_mini_dataset(tmp_path_factory.mktemp("mini"))
    ec = build_context(d)
    return {r["case_id"]: analyze_case(r, ec) for r in ec.ctx.requests}


@pytest.mark.parametrize("case_id", sorted(EXPECTED))
def test_mini_case_matches_hand_derived_answer(mini, case_id):
    status, steps = EXPECTED[case_id]
    got = mini[case_id]
    assert got.deletion_status == status
    assert got.steps == steps
