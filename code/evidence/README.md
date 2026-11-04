# Evidence Discovery module (`code/evidence/`)

Discovers and reads every file listed in `dataset/evidence_files.csv` and exposes
normalised observations to the auditor. **It makes no policy decisions**: no
`deletion_status`, no `steps_json`, and it never drops retained, tombstone or
replica records.

## Setup and run

```bash
python -m venv .venv                       # at the repository root
.venv/Scripts/pip install -r code/requirements.txt     # Windows
# .venv/bin/pip install -r code/requirements.txt       # macOS / Linux

python code/evidence/__main__.py --per-file             # full-corpus scan report
cd code && python -m pytest                             # tests
RUN_OCR_TESTS=1 python -m pytest -m ocr                 # also run the live OCR engine
python code/evidence/ocr_cache_build.py [--force]       # rebuild the OCR cache
```

## API (used from `code/main.py`)

```python
from evidence import EvidenceScanner, SubjectIdentifiers

scanner = EvidenceScanner(dataset_dir)        # ocr_mode="auto" | "cache_only" | "force"
scanner.load()                                # parse all 94 files once

ids = SubjectIdentifiers(user_id="user_05", emails=frozenset({...}), phones=..., email_hashes=...,
                         names=..., resource_ids=frozenset({"account_001"}))   # resource ids e.g. from system_activity
audit_at = datetime(2026, 9, 3, 11, 30, tzinfo=timezone.utc)   # must be timezone-aware
hits   = scanner.find_records(ids, audit_at)          # list[ObservedRecord]: every observation, claims included
latest = scanner.latest_by_resource(ids, audit_at)    # {(system_id, resource_id, replica_or_table): ObservedRecord}
                                                      #   authoritative only; include_claims=True to let claims compete
proofs = scanner.absence_proofs("account_service", "account_001", audit_at)   # list[AbsenceProof], COMPLETE only
                                                      #   include_unverified=True adds INFERRED / INCOMPLETE candidates
scanner.records_for_resource("analytics_9406", audit_at)
scanner.files(); scanner.get_file("evidence_54"); scanner.issues; scanner.summary()
```

`find_for_subject(ids, audit_at)` is kept as a backward-compatible alias of `find_records` (identical results).

* **`audit_at` validation**: a timezone-aware `datetime`, or an ISO-8601 string with an explicit offset
  (`Z` / `+HH:MM`). Naive datetimes and offset-less strings raise `ValueError`; other types raise `TypeError`.
* **Cutoffs**: a record is returned only if the file's manifest `captured_at` **and** the record's own
  `observed_at` are `<= audit_at` (inclusive).
* **`replica_or_table`** is `None` for the primary / system-of-record copy and the replica name otherwise
  (`customer_profiles_failover_replica`, `customer_data_read_replica`, `support_replica`, ...).
* **`presence`**: `PRESENT`, `ABSENT` (404 / rows=0 / NOT_FOUND / zero hits) or `UNKNOWN`.
* **`claim_only=True`** marks second-hand lookup ledgers (handover TXT, `record_lookup` logs,
  export-manifest / connector / security-audit ledgers, `operational_record_history`). Snapshots,
  SQL rows, completed read-backs, PII scans, PDFs and screenshots are `claim_only=False`.
* **`pii_fields`** holds only direct identifiers stored in the record (non-null). Query keys such as
  `lookup_key` link a record to a subject but are never reported as exposed PII. A tombstone with null
  name/email/phone/hash is `PRESENT` with `pii_fields == {}` and keeps its `subject_reference`.
* **Linking**: identifiers match exactly after normalisation (emails case-insensitive, phones digits only,
  names case/accent-insensitive full-name equality, `user_*` exact). Direct matches are then expanded
  through resource ids (and attachment file names) so de-identified later copies are found.
* **Absence**: `SnapshotScope`s record which collections a snapshot fully enumerated (JSON bundles,
  collection dumps, SQL tables, inventory `snapshot_scope`). `absence_proofs` returns the in-window scopes
  of the same system and data category that do not contain the resource. Each `AbsenceProof` carries
  `scope_source`, `completeness` (`COMPLETE` / `INFERRED` / `INCOMPLETE`), `scope_record_count`,
  `limitations` (which copy it covers, inference caveats), `errors` (parse issues of the file) and
  `contradicted_by` (later authoritative PRESENT observations of the same copy). Only `COMPLETE` proofs
  are returned by default: coverage inferred from sibling SQL tables, and files with parse issues, are
  never treated as proof. `proof.is_valid_proof` = COMPLETE and not contradicted; `proof.verified_at` is
  the snapshot time.

## Layout

| File | Role |
|---|---|
| `models.py` | `EvidenceFile`, `SubjectIdentifiers`, `ObservedRecord`, `SnapshotScope`, `AbsenceProof`, `ParseIssue` |
| `manifest.py` | loads and validates the manifest (missing / unlisted / duplicate / unsupported files) |
| `normalize.py` | identifier normalisation, free-text extraction, resource-prefix and collection vocabularies |
| `parsers/json_records.py` | snapshot bundles, service exports, lookup ledgers, collection dumps |
| `parsers/sql_snapshots.py` | executes each dump in in-memory SQLite; blob, inventory and typed tables |
| `parsers/logs.py` | 6 line syntaxes / 9 file families, trace-id correlation of `*_started` and `*_completed` |
| `parsers/pdf_documents.py` | pypdf text; register rows, resource mentions, single-subject documents |
| `parsers/images.py` | RapidOCR + SHA-256-keyed cache in `ocr_cache/`, row-aware identifier linking |
| `parsers/text_handover.py` | pipe-delimited handover checklist |
| `index.py`, `scanner.py` | inverted index and the public API |
