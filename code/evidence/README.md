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

```python
refs = scanner.referenced_resources(ids, audit_at)    # list[ResourceReference]: ids named inside the subject's
                                                      #   confirmed, authoritative, in-window observations
for r in refs:                                        #   e.g. account_006 via evidence_57 source_resource_id
    scanner.absence_proofs(r.system_id, r.resource_id, audit_at)
```

* **Identity assessment** (on every record returned by `find_records`):
  `match_strength` is `STRONG` (email / phone / email_hash / user_id / supplied resource id), `LINKED`
  (followed from a confirmed observation; `linked_via` gives `evidence_id@locator`) or `WEAK` (exact full
  name only; a name never establishes ownership). `identity_conflict` + `conflict_details` flag records
  whose stored `user_*` reference disagrees with the subject's `user_id`, or that carry the subject's
  `user_id` with a different owner email / phone / hash. `rec.is_confirmed` = STRONG or LINKED and no
  conflict. WEAK and conflicting records are still returned, but they never seed link expansion or
  `referenced_resources`, and `latest_by_resource` ignores them unless `include_unconfirmed=True`.
  Claim-only records may point at their own resource id but their cross-references are never followed.
* **File-name links** use only real file-name fields (`file_name`, `file`, screenshot file names).
  Archive paths and object keys (`segment-31.tar.zst`, `customer_data.zip`) are shared storage locations
  and are never used to link records.

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
| `integration.py` | P1 identity bundle -> findings dictionary for P3 (`find_evidence`, `get_scanner`) |

## Integration with P1 and P3 (`integration.py`)

```python
from evidence.integration import find_evidence, get_scanner

findings = find_evidence(identity, audit_at)   # identity: P1 IdentityBundle; audit_at: tz-aware datetime
# optional: scanner=..., or dataset_dir=... / ocr_mode=... for get_scanner()

from evidence.integration import find_case_evidence
findings = find_case_evidence(identity, case)  # case: a deletion_requests.csv row (dict)
```

`find_case_evidence(identity, case)` returns exactly `find_evidence(identity, case_audit_at(case))`.
`case_audit_at(case)` accepts `case["audit_at"]` as a timezone-aware `datetime` or an ISO-8601 string
with an explicit offset (`Z`, `+HH:MM`, `-HHMM`), as stored in the CSV. Missing/empty values, naive
datetimes and offset-less strings raise `ValueError`; other types, or a `case` that is not a mapping,
raise `TypeError`.

* Identifiers come from P1's adapter exactly: `SubjectIdentifiers(**identity.as_subject_kwargs())`.
  Nothing from P1 is imported; only the attributes documented in `code/README_identity.md` are read
  (`as_subject_kwargs()`, `user_id`, `current_email`, `current_phone`, `current_email_hash`,
  `current_name`, `history[*].audit_id/field_name/old_value/new_value/event_time`).
* `get_scanner(dataset_dir=None, *, ocr_mode="auto")` loads the corpus once per process for each
  (resolved dataset directory, OCR mode); `find_evidence` uses it unless `scanner=` is passed.
* One validated cutoff is used for every scanner call. `audit_at` missing or naive -> `ValueError`;
  not a `datetime` -> `TypeError`. A `history` row dated after `audit_at` -> `ValueError` (the bundle was
  resolved for another cutoff). An identifier in `as_subject_kwargs()` that neither the snapshot fields nor
  `history` explain -> `ValueError` (nothing is guessed).
* The scanner APIs (`find_records`, `latest_by_resource`, `referenced_resources`, `absence_proofs`) are
  called unchanged with their safe defaults.

### Returned dictionary (exactly five keys)

| Key | Type | Semantics |
|---|---|---|
| `records` | `list[ObservedRecord]` | `scanner.find_records(identifiers, audit_at)`: every in-window observation, including claim-only (`claim_only=True`), name-only (`match_strength="WEAK"`) and conflicting (`identity_conflict=True`) ones, with `identifiers_matched` and `linked_via` provenance. Nothing is collapsed. |
| `latest_by_resource` | `dict[tuple[str, str, Optional[str]], ObservedRecord]` | Key `(system_id, resource_id, replica_or_table)`, `replica_or_table=None` for the primary copy. Latest **authoritative, confirmed** observation per copy (`scanner.latest_by_resource` defaults): no claims, no WEAK, no conflicts. |
| `referenced_resources` | `list[ResourceReference]` | Resource ids named inside confirmed, non-claim, in-window observations (e.g. `source_resource_id`), with source evidence id, locator and field. Pointers only; `has_observations` says whether the resource has any in-window observation. |
| `absence_proofs` | `dict[tuple[str, str], list[AbsenceProof]]` | Key `(system_id, resource_id)`, deduplicated case-insensitively. One key per referenced resource with a known `system_id` and per resource of a confirmed, non-claim observation. Values hold only valid proofs (`completeness == "COMPLETE"` and not `contradicted_by`); an empty list means the scanner could establish no valid proof. Claims never create a key. |
| `identifier_provenance` | `dict[tuple[str, str], list[dict]]` | Key `(kind, normalised_value)` for every searched identifier, normalised as the scanner matches (so `f"{kind}:{value}"` equals an `identifiers_matched` label). `kind` is `user_id`, `email`, `phone`, `email_hash` or `name`. Each entry: `{"source", "audit_id", "event_time", "basis"}` (see below). |

Provenance entries:

| Field | Type | Meaning |
|---|---|---|
| `source` | `"CURRENT"` \| `"HISTORICAL"` | HISTORICAL = an `old_value` in `identity.history`; CURRENT = the bundle's current email/phone/hash, `user_id` or `current_name`. A value that was both gets one entry each. |
| `audit_id` | `str` \| `None` | HISTORICAL: the history row whose `old_value` it is. CURRENT: the row whose `new_value` made it current, else `None`. `None` for computed hashes. Never invented. |
| `event_time` | `datetime` \| `None` | Aware UTC. HISTORICAL: when it **stopped** being current (P1: "used until `event_time`"). CURRENT: when it **became** current. `None` if P1's `event_time` is empty or there is no row. |
| `basis` | `str` | `history.old_value`, `history.new_value`, `snapshot`, or `computed_sha256_of_historical_email` (P1 adds the SHA-256 of each historical email; such a hash may have no audit row). |

Historical identifiers are included because their change is at or before `audit_at`; evidence is **not**
filtered by the identifier's validity window. Old identifiers that still appear after they were changed
are exactly the ghost data the auditor must find (all 214 historical matches in the corpus are of this kind).
