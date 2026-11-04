import collections
import re
from datetime import datetime, timezone

from evidence.manifest import SUPPORTED_EXTENSIONS, load_manifest
from evidence.models import SubjectIdentifiers


def test_manifest_has_94_entries_all_on_disk(dataset_dir):
    rep = load_manifest(dataset_dir)
    assert len(rep.files) == 94
    assert rep.missing_on_disk == []
    assert rep.unlisted_on_disk == []
    assert rep.duplicate_ids == []
    assert rep.unsupported == []
    for f in rep.files:
        assert f.absolute_path.is_file(), f.file_path


def test_manifest_ids_are_valid_and_unique(dataset_dir):
    rep = load_manifest(dataset_dir)
    ids = [f.file_id for f in rep.files]
    assert len(set(ids)) == 94
    assert all(re.fullmatch(r"evidence_\d{2}", i) for i in ids)
    assert ids[0] == "evidence_01" and ids[-1] == "evidence_94"


def test_manifest_extension_counts(dataset_dir):
    rep = load_manifest(dataset_dir)
    counts = collections.Counter(f.extension for f in rep.files)
    assert counts == {"log": 26, "json": 28, "sql": 24, "png": 11, "pdf": 4, "txt": 1}
    assert set(counts) == set(SUPPORTED_EXTENSIONS)


def test_manifest_timestamps_are_utc(dataset_dir):
    rep = load_manifest(dataset_dir)
    f = next(x for x in rep.files if x.file_id == "evidence_54")
    assert f.captured_at == datetime(2026, 9, 2, 23, 0, tzinfo=timezone.utc)
    assert f.file_path == "evidence/databases/customer_accounts_failover_replica_20260902.sql"
    assert f.origin == "customer_account_failover_replica_capture"


def test_subject_identifiers_normalisation():
    s = SubjectIdentifiers(
        user_id="USER_05",
        emails=frozenset({"BCARVALHO6517@GMAIL.COM", " x@y.io "}),
        phones=frozenset({"+212 6 48 27 15 93"}),
        email_hashes=frozenset({"ABCDEF" * 11}),
        names=frozenset({"  Léila   HADDAD "}),
        resource_ids=frozenset({"Account_005"}),
    ).normalized()
    assert s.user_id == "user_05"
    assert s.emails == {"bcarvalho6517@gmail.com", "x@y.io"}
    assert s.phones == {"212648271593"}
    assert s.names == {"leila haddad"}
    assert s.resource_ids == {"account_005"}
