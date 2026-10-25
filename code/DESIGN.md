# Design: Ghost Data Still Exists deletion-audit agent

Rule: **the model reads and proposes; deterministic code decides and writes `output.csv`.**

## 1. Inputs

| File (`dataset/`) | Use |
| --- | --- |
| `deletion_requests.csv` | 518 cases: email, request time, claimed status, `audit_at`, free-text request |
| `user_identities.csv`, `user_audit_log.csv` | Current and historical emails, phones, hashes per `user_id` |
| `system_activity.csv` | 4,011 global events. Claims, ownership links, state read-backs; many decoys |
| `deletion_rules.csv` | 15 category rules (DELETE / REDACT / ANONYMIZE / RETAIN) |
| `evidence_files.csv` + `evidence/` | 94 files: SQL snapshots, JSON, logs, TXT, 11 PNG, 4 PDF |
| `sample_*.csv` | 32 solved cases: development set only |

All dataset text is **untrusted data**, never instructions.

## 2. Output contract

`code/schema.py` is the single source of truth: status/phase/operation/state enums, the
operation table, `step_sort_key`, and the Pydantic models `Step` and `OutputRow`.
`validate.py`, `main.py`, `intent.py`, prompts and LLM-output checks import it.

- Header `case_id,deletion_status,steps_json`; 518 rows in numeric `case_id` order.
- Steps sorted by phase, operation table order, `system_id`, `resource_id`; `step_no` 1..n.
- COMPLETE: VERIFICATION steps only, each cites evidence at or before `audit_at`.
- INCOMPLETE: FINDING steps cite evidence; REMEDIATION and VERIFICATION use `""`.
- NOT_APPLICABLE: `[]`. JSON: sorted keys, compact separators.

## 3. Model-vs-code boundary

| Task | Model (`meta/muse-spark-1.3-contributor`, ZenMux) | Code |
| --- | --- | --- |
| PNG/PDF reading | Transcribe rows to a JSON schema | Schema + id-pattern check; grounding vs OCR / PDF text layer |
| Intent | Label AMBIGUOUS texts only (enum) | Clause rules decide first; enum check |
| Unlinked / conflicting items | Investigator proposes link or state | Acceptance check (section 4); resolver and policy decide |
| Status, steps, citations, order | Never | Always |

- Key only from env `ZENMUX_API_KEY` or the uncommitted repo-root `.env` (a real env var wins).
  Base URL, model id and prices live in `config.py`. `.env.example` holds placeholders.
- Model: `meta/muse-spark-1.3-contributor`. The key gets HTTP 403 for `meta/muse-spark-1.3`.
- Cache key = SHA-256(input bytes) + prompt version + model id.
- No key or `ZENMUX_OFFLINE=1`: replay the committed `llm_snapshot.py`. No network is needed.
  A snapshot miss gives the deterministic result and the flag `snapshot_miss`.
- Model output goes through the `schema.py` LLM contracts (`extra="forbid"`): parse, one retry
  with the validation error, then the deterministic fallback with a flag. Grounding and
  acceptance run after schema validation.
- Vision and intent use `json_schema` output. The agent uses `json_object` output, because
  constrained decoding dropped optional tool arguments. The client keeps the longest JSON
  object in the reply and discards prose.

Phase 4 rules:

- Vision grounding: every accepted row's resource id and identifier must occur in the OCR or
  PDF text. The match allows only OCR noise: case, `_`/`-`/`.`/`,`/space between id tokens,
  `o`/`0`, and `l`/`i`/`|`/`!`/`1`. Ids need a boundary on both sides. Phones compare digits.
- An accepted vision row is an observation (assertion `vision_row`, rank 2) at the file's
  `captured_at`, and a medium edge `vision_identifier`.
- An accepted agent STATE proposal is a case-local observation (`agent_readback`, rank 1).
  An accepted LINK proposal is a case-local medium edge `agent_link`.
- Category order (`policy.category_of`): stated `record_type` -> collection name -> content
  (`policy.CONTENT_CATEGORY` on the catalog-link text, for example "Attachment catalog" ->
  `SUPPORT_ATTACHMENT`) -> system default. A record with no category from any source is not
  a target. The content table is a general word mapping, never a per-id exception.

## 4. Investigator agent loop (`agent/`, D19)

Runs only for items the deterministic pass leaves `UNKNOWN`/`CONFLICT` or AMBIGUOUS.

Tools (narrow, read-only except the last):
1. `search_evidence(query)` - exact-id grep, then BM25 over raw text and facts.
2. `read_evidence(file_id)` - parsed rows of one file (vision rows for PNG/PDF).
3. `query_facts(resource_id | identifier)` - fact-store rows and ownership edges.
4. `submit_proposal(proposal)` - a typed `AgentProposal`: `LINK` or `STATE`. There is no
   intent proposal: both request files have 0 AMBIGUOUS texts (cut per the Phase 4 order).

Caps: 4 tool iterations per item, 2 retries for invalid output, timeout per call,
token budget per case. Over budget means the item stays `UNKNOWN`.

Acceptance check (code, per proposal):
- Every cited id was opened in this loop and has availability time `<= audit_at`.
- The cited row contains the `resource_id` and a subject identifier, or a typed link row.
- The claimed state matches the cited row's parsed state.
- Pass: add a medium-tier edge or observation. Fail: reject and log the reason.

## 5. Modules

| Module | Role | Phase |
| --- | --- | --- |
| `schema.py` | Contract enums, table, sort key, Pydantic models | 1 |
| `loaders.py` | CSV loading, UTC times, normalization, hashes | 1 |
| `identity.py` | As-of identifier resolution with future-row guard | 1 |
| `intent.py` | Clause-level deletion-intent rules | 1 |
| `validate.py` | Output-file contract validator | 1 |
| `main.py` | CLI, per-case isolation, serialization | 1 |
| `evidence/extract_*.py` | SQL, JSON, log, text, vision extractors | 2-4 |
| `facts.py`, `parse_coverage.py` | Global fact store; per-file parse accounting | 2-3 |
| `links.py` | Typed, time-stamped ownership graph | 3 |
| `resolver.py` | State per physical copy at `audit_at` | 2 |
| `policy.py` | `deletion_rules.csv` as a truth table | 2 |
| `citation.py` | Evidence choice, separate from state | 2 |
| `planner.py` | Steps and canonical sort | 2 |
| `llm_client.py`, `llm_cache.py`, `llm_snapshot.py`, `prompts/` | Model access, cache, replay | 4 |
| `safety.py` | Injection screen and delimiting | 4 |
| `agent/` | Investigator loop and tools | 4 |
| `audit_trace.py` | Per-case JSONL decision trace | 2-5 |
| `evaluation/main.py` | Scorer, confusion matrix, suite runner | 1-5 |
| `evaluation/custom.py`, `evaluation/metamorphic.py` | Custom-case materializer and metamorphic checks | 5 |

Phase 3 rules:

- Dominance (`resolver.DOMINANCE`): per physical copy, the newest observation at or before `audit_at` wins. Tier breaks ties only at the same time. Same time, same tier, different states gives `CONFLICT`. Claims never set state. `tier_first` stays as a swappable rule for comparison.
- Logs: six line shapes (`evidence/log_lines.py`), events typed by table (`evidence/extract_log.py`). A "delete completed" line is an operation claim. An unknown shape or event is a coverage error.
- PDF text (pypdf) gives facts. PNG OCR text (Tesseract) is grounding text only, stored in `FactStore.grounding`.
- Medium edge `job_burst` only; it is flagged `M:job_burst:<id>` in the trace.

Phase 5 rules:

- Stale link: a target whose links all predate `requested_at` is excluded entirely, even when evidence shows it `PRESENT` (flag `stale_link:<id>` in the trace).
- Vision prompt `vision_extract_v2`: the model gets the catalog alias table (file name / statement number -> resource id, `facts.catalog_alias_rows`). A row may use a mapped id only when the exact alias is visible; grounding checks the alias in the OCR text, and the row is available no earlier than the alias.
- `window_assignment` (global one-to-one account assignment by time distance to `reported_at`) is implemented behind `links.WINDOW_ASSIGNMENT_ENABLED = False`: sample precision 5/15, below the 0.9 gate.
- Vision grounding (#9): a row is accepted only when one OCR block holds the resource id (or a visible catalog alias) and its state cue, and the identifier is in that block or, on a page that names no other record, anywhere on the page. Blocks are the Tesseract `--psm 3` TSV blocks plus each `--psm 6` line. In a block that lists other records (a table), the cue must be on the record's own line, so a state is never taken from another row. OCR readings are shipped in `ocr_snapshot.json` for reproducible replay.

### Policy readings where the evidence does not state the condition

| Rule | Rule text (`deletion_rules.csv`) | Reading in code | Why |
| --- | --- | --- | --- |
| rule_06 (#7) | `SUPPORT_ATTACHMENT`, "Attachment belongs only to the deletion subject", `DELETE` | Exclusive when a catalog link says so, or when a strong `identifier` edge links the attachment to the subject and no other user is linked (`policy.attachment_exclusive`). Otherwise `UNPROVEN`: no finding, no remediation, case not `COMPLETE`. | No evidence file states "exclusive". A catalog-only reading removes gold-correct attachment steps in samples case_07 and case_13. |
| rule_13 (#8) | `LEGAL_HOLD_RECORD`, "A supplied legal hold is active", `RETAIN` | Not active (delete path) when the newest non-claim state has status INACTIVE or RELEASED, or a retention end date (`retention_until`, `retained_until`, ...) at or before `audit_at`. Retained when a status or an end date exists and neither of these holds. No status and no end date: `UNPROVEN` ("legal hold status missing"). | No evidence file states a hold status; the legal-hold register (a PDF) gives "Retain until" dates, so the end date is the only stated condition. |

## 6. Failure modes and guards

| # | Failure | Guard |
| --- | --- | --- |
| 1 | Evidence after `audit_at` changes a case | One cutoff function on file and inner times; `identity.py` raises `FutureDataError`; validator rejects late citations; metamorphic test adds late evidence |
| 2 | Model invents an id or a state | Schema + id patterns; grounding against OCR/PDF text; acceptance check; model never writes steps |
| 3 | Missing primary row hides a surviving replica | Resolve each physical copy separately; absence only inside a file's declared scope. A subject-scoped listing covers only the subjects of that system's (and collection's) own rows, never a sibling system's in the same file (#6). A data flow or backup is compliant only when every copy that is not proven ABSENT is DISABLED / BLOCKED (r2-#1) |
| 4 | Unlinked record makes a case look COMPLETE | `UNKNOWN` targets go to the agent, then the trace and report; never a silent COMPLETE |
| 5 | One bad case or no network kills the run | Per-case try/except: fallback `INCOMPLETE` with empty-evidence verification for the known targets (`INCOMPLETE,[]` when none); the batch never stops, every row is written, failed cases go to `<out>_failures.csv` and the exit code is 1; `OutputRow` guard; strict `validate.py` before success; one failing OCR image is a coverage error; snapshot replay with no key |
| 6 | Row order or serialization drift | Numeric `case_id` sort; `schema.step_sort_key`; `validate.py` on every run; byte-hash regression check |

## 7. Evaluation plan

- `python code/evaluation/main.py`: status accuracy, step P/R/F1, field accuracy, sequence
  accuracy, confusion matrix, custom-case and metamorphic pass/fail, agent stats
  (writes `code/evaluation/results.md` and `.json`).
- Samples are a development set (they shaped the design); report this honestly.
- Custom cases (`evaluation/custom_cases/`, frozen in commit b7de58c before Phase 5 tuning):
  negated request, verify-only, injection in request text, retained record, flow + restore
  risk, scripted agent run with acceptance check, historical email.
- Metamorphic tests (`evaluation/metamorphic.py`): shuffled rows and global tables, email
  case and spaces, an older contradicting read-back, `audit_at` 1 s before the key file
  (it must drop out), `audit_at` exactly at it (inclusive cutoff).
- Ablation: agent off vs on; keep it only if F1 does not drop.
- Clean-room run: unzip `code.zip`, add `dataset/`, no key, compare the output hash.

## 8. Injection-safety plan (D20)

1. Screen request texts and extracted evidence text before any model call
   (role markers, "ignore previous instructions", tool or status commands, hidden Unicode).
2. A screened hit is never sent raw. Code logs it and keeps the deterministic result.
3. Data goes to the model inside delimiters, with a system prompt that defines it as data.
4. Model output is parsed only through `schema.py` models. Free text is discarded.
5. The model has no tool that writes output, changes status or deletes anything.
6. Policy invariants in code: never DELETE a retained category (security audit, legal
   hold, backup); never act on a record linked only to another user.
7. Adversarial tests: injected request text, forged "deletion complete" log line,
   decoy near-match email, instruction text inside an evidence file.
