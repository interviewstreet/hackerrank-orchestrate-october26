"""Regression tests for issues found in the final code review."""

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from evidence import EvidenceScanner, SubjectIdentifiers
from evidence.models import EvidenceFile
from evidence.parsers import images, parse_file


# ---- absence_proofs never infers absence outside a scope's own category ----
def test_absence_unknown_category_returns_no_proof(scanner):
    # support_* is ambiguous (message vs attachment) and this id is never observed
    assert scanner.absence_proofs("support_platform", "support_99999", "2026-09-30T00:00:00Z") == []


def test_absence_only_uses_matching_category_and_system(scanner):
    proofs = scanner.absence_proofs("support_platform", "support_99999", "2026-09-30T00:00:00Z",
                                    data_category="SUPPORT_ATTACHMENT")
    assert proofs and all(p.data_category == "SUPPORT_ATTACHMENT" and p.system_id == "support_platform" for p in proofs)
    for p in proofs:
        sc = [s for s in scanner.scopes if s.evidence_id == p.evidence_id and s.collection == p.collection
              and s.replica_or_table == p.replica_or_table]
        assert sc and not sc[0].contains("support_99999")


def test_absence_proofs_respect_cutoff(scanner):
    audit_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    for p in scanner.absence_proofs("account_service", "account_001", audit_at):
        assert p.captured_at <= audit_at and scanner.get_file(p.evidence_id).captured_at <= audit_at


# ---- identity preserved ---------------------------------------------------
def test_resource_id_original_casing_preserved(scanner):
    reg = sorted(r.resource_id for r in scanner.records if r.evidence_id == "evidence_27")
    assert reg[0] == "ORD-20264118"
    hits = scanner.find_for_subject(SubjectIdentifiers(resource_ids=frozenset({"ord-20264118"})), "2026-06-01T00:00:00Z")
    assert [h.resource_id for h in hits] == ["ORD-20264118"]
    assert scanner.records_for_resource("Ord-20264118", "2026-06-01T00:00:00Z")


def test_identity_fields_survive_retrieval(scanner):
    by_loc = {(r.evidence_id, r.locator): r for r in scanner.records}
    ids = SubjectIdentifiers(emails=frozenset({"leila.haddad@yahoo.com", "novak.tomasz@icloud.com"}))
    for h in scanner.find_for_subject(ids, "2026-10-01T12:00:00Z"):
        src = by_loc[(h.evidence_id, h.locator)]
        assert (h.system_id, h.resource_id, h.replica_or_table, h.collection, h.observed_at, h.captured_at) == \
               (src.system_id, src.resource_id, src.replica_or_table, src.collection, src.observed_at, src.captured_at)


# ---- OCR cache invalidation and recovery ----------------------------------
@pytest.fixture
def ocr_sandbox(tmp_path, monkeypatch):
    from PIL import Image

    monkeypatch.setattr(images, "CACHE_DIR", tmp_path / "cache")
    calls = []

    def fake_ocr(path):
        calls.append(path)
        return [{"text": "account_42 a@b.io", "conf": 0.9, "box": [[0, 0], [10, 0], [10, 10], [0, 10]]}]

    monkeypatch.setattr(images, "run_ocr", fake_ocr)
    img = tmp_path / "screen.png"
    Image.new("RGB", (30, 20), "white").save(img)
    return img, calls


def _ev(path):
    return EvidenceFile("evidence_99", "evidence/images/screen.png", "test", datetime(2026, 1, 1, tzinfo=timezone.utc), path)


def test_ocr_cache_miss_then_hit(ocr_sandbox):
    img, calls = ocr_sandbox
    assert images.load_ocr(img)[1] == "engine"
    assert images.load_ocr(img)[1] == "cache"
    assert len(calls) == 1


def test_ocr_cache_invalidated_when_image_changes(ocr_sandbox):
    from PIL import Image

    img, calls = ocr_sandbox
    images.load_ocr(img)
    Image.new("RGB", (30, 20), "black").save(img)
    assert images.load_ocr(img)[1] == "engine" and len(calls) == 2
    assert images.load_ocr(img, "cache_only")[1] == "cache"


def test_ocr_corrupt_cache_recovers(ocr_sandbox):
    img, calls = ocr_sandbox
    images.load_ocr(img)
    entry = next(images.CACHE_DIR.glob("*.json"))
    entry.write_text("{not json", encoding="utf-8")
    with pytest.raises(images.OCRUnavailable):
        images.load_ocr(img, "cache_only")
    items, source = images.load_ocr(img, "auto")
    assert source == "engine" and items and len(calls) == 2
    assert json.loads(entry.read_text(encoding="utf-8"))["items"] == items  # rewritten
    assert not list(images.CACHE_DIR.glob("*.tmp"))


def test_ocr_cache_with_wrong_digest_is_ignored(ocr_sandbox):
    img, calls = ocr_sandbox
    images.load_ocr(img)
    entry = next(images.CACHE_DIR.glob("*.json"))
    data = json.loads(entry.read_text(encoding="utf-8"))
    data["sha256"] = "0" * 64
    entry.write_text(json.dumps(data), encoding="utf-8")
    assert images.load_ocr(img)[1] == "engine"


def test_ocr_force_reruns_engine(ocr_sandbox):
    img, calls = ocr_sandbox
    images.load_ocr(img)
    assert images.load_ocr(img, "force")[1] == "engine" and len(calls) == 2


def test_ocr_unwritable_cache_still_parses(ocr_sandbox, monkeypatch, tmp_path):
    img, _ = ocr_sandbox
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x", encoding="utf-8")  # mkdir/write under a file fails with OSError
    monkeypatch.setattr(images, "CACHE_DIR", blocker / "cache")
    r = parse_file(_ev(img), ocr_mode="auto")
    assert [x.resource_id for x in r.records] == ["account_42"] and not r.issues


# ---- data access confinement ----------------------------------------------
def test_manifest_paths_outside_evidence_are_refused(tmp_path):
    ds = tmp_path / "dataset"
    (ds / "evidence").mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("- 2026-01-01T00:00:00Z | account_service | account_1 | USER_PROFILE | FOUND | x@y.io\n", encoding="utf-8")
    (ds / "evidence_files.csv").write_text(
        "file_id,file_path,origin,captured_at\nevidence_01,../secret.txt,test,2026-01-01T00:00:00Z\n", encoding="utf-8")
    s = EvidenceScanner(ds)
    s.load()
    assert s.records == []
    assert [i.message for i in s.issues if i.evidence_id == "evidence_01"] == ["manifest path is outside dataset/evidence/; not read"]


def test_sql_attach_is_denied(tmp_path):
    (tmp_path / "evidence/databases").mkdir(parents=True)
    target = tmp_path / "planted.db"
    sql = tmp_path / "evidence/databases/x.sql"
    sql.write_text(f"ATTACH DATABASE '{target.as_posix()}' AS x; CREATE TABLE x.t(a);", encoding="utf-8")
    ev = EvidenceFile("evidence_01", "evidence/databases/x.sql", "t", datetime(2026, 1, 1, tzinfo=timezone.utc), sql)
    r = parse_file(ev)
    assert r.issues and r.issues[0].severity == "error"
    assert not target.exists()
