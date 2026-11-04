import csv
import shutil

from engine.validate_output import validate_output_csv


def test_generated_output_is_valid(root):
    assert validate_output_csv(root / "output.csv", root / "dataset") == []


def test_validator_rejects_bad_files(root, tmp_path):
    rows = list(csv.reader(open(root / "output.csv", encoding="utf-8", newline="")))
    bad = tmp_path / "bad.csv"
    for mutate, needle in [
        (lambda r: r[:-1], "rows"),                                   # missing row
        (lambda r: [r[0]] + r[2:3] + r[1:2] + r[3:], "sorted"),       # unsorted
        (lambda r: r[:1] + [[r[1][0], "MAYBE", r[1][2]]] + r[2:], "bad status"),
        (lambda r: r[:1] + [[r[1][0], r[1][1], "not json"]] + r[2:], "JSON"),
    ]:
        with open(bad, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerows(mutate([list(x) for x in rows]))
        assert any(needle in p for p in validate_output_csv(bad, root / "dataset")), needle


def test_output_has_one_row_per_request_sorted(root):
    ids = [r[0] for r in list(csv.reader(open(root / "output.csv", encoding="utf-8", newline="")))[1:]]
    assert len(ids) == 518 and ids == sorted(ids) and len(set(ids)) == 518
