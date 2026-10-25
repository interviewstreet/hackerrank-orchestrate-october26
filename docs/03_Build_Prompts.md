# 03 — Build Prompts (copy-paste into your AI coding tool, in order)

**How to use:** open your coding tool **at the repo root**. Paste one prompt at a time. After each, run what it built and look at the output. Only move on when the "Check" line passes. If a prompt is too big for the tool, paste the sub-bullets separately.

Attach or point the tool to: `AGENTS.md`, `problem_statement.md`, and this playbook's `01_Problem_Analysis.md` + `02_Architecture.md` (copy them into `docs/` or paste when asked).

---

## P0 — Bootstrap (always first)

```
Read ./AGENTS.md completely and follow it exactly: log SESSION START and every turn to ./log.txt
in the required format (tool= and model= must be the real values from your runtime; if you cannot
determine the exact model identifier, ask me instead of guessing).

Then read ./problem_statement.md and ./README.md. Then read docs/01_Problem_Analysis.md and
docs/02_Architecture.md, which are my project's analysis and design.

Rules for this whole project:
- Python 3.10+, standard library + pandas, pillow, pytesseract, pdfplumber. No other heavy deps.
- Entry point: python3 code/main.py  -> reads ./dataset/, writes ./output.csv at repo root.
- Never hardcode case IDs, resource IDs, user IDs, or sample answers. Logic must generalize.
- Only use files under ./dataset/. Ignore anything dated after a case's audit_at.
- reported_status and activity reported_result are claims, not proof.
- Deterministic output (stable sorting, json.dumps with separators=(",",":")).
- Read API keys only from environment variables. Never print or log them.
- After each task, run the code and show me real output. Do not claim success without running.

Confirm you understand by summarizing in 8 bullets: the output schema, the operation order tables,
the time-cutoff rule, and the build plan. Do not write code yet.
```
**Check:** the tool replies with the summary and `log.txt` has a SESSION START entry with non-empty `tool=` and `model=`.

---

## P1 — Explore the data and write notes

```
Write code/evaluation/explore.py and run it. It must print and save to code/evaluation/data_notes.md:
1. Row counts and columns of every CSV in dataset/.
2. For deletion_requests.csv: counts by reported_status; number of unique request_text; the first
   10 unique texts; the list of languages you can detect.
3. For system_activity.csv: counts by event_type, source_system, target_system, reported_result;
   the resource_id prefix families and counts.
4. For evidence_files.csv: counts by origin and by folder, and check every file_path exists.
5. For each evidence format (sql, json, log, txt, pdf, png) show one short sample (first ~20 lines;
   for pdf use pdftotext/pdfplumber; for png use pytesseract) and list every distinct JSON "shape"
   (top-level keys) and every distinct log line template (replace values with placeholders).
6. For all 32 sample cases: print case_id, request email, whether it matches a current email or a
   historical (old) email, reported_status, audit_at, deletion_status, and the compact step list
   (phase initial, system, resource, operation, evidence_id). Group cases by identical step "shape".
7. Print which evidence file_ids are cited in sample_output.csv and their captured_at vs the case audit_at.
Keep output concise. Then summarize any surprise you find vs docs/01_Problem_Analysis.md.
```
**Check:** `data_notes.md` exists; you can read the sample shapes and see which evidence IDs samples cite.

---

## P2 — Loaders + identity resolver

```
Implement code/audit/config.py, loaders.py, identity.py.

config.py: path constants resolved relative to repo root (works on Windows/macOS/Linux),
PHASE_ORDER, OP_ORDER, OP_STATE exactly as in docs/01_Problem_Analysis.md section 5.

loaders.py: load all CSVs (utf-8, keep strings), parse timestamps to timezone-aware UTC datetimes
(helper parse_ts), natural-sort helper for case_id by numeric suffix.

identity.py: class IdentityResolver(user_identities, audit_log):
 - resolve(email) -> user_id (lowercase/strip; searches current emails AND every old/new email value in
   the audit log; also email_hash via sha256(lower(email))).
 - identifiers(user_id, audit_at) -> dict with sets: emails, hashes, phones, user_ids (include the
   user_id), name (single, secondary hint).
Include old_value AND new_value of every audit event for that user (historical values are always safe
to include). Document in a docstring how you treat changes dated after audit_at.
Write tests in code/evaluation/test_identity.py: all 518 requests resolve; count current-vs-historical
matches and print them (expect 418 current, 100 historical).
```
**Check:** test prints 518 resolved, ~418/100 split.

---

## P3 — Intent classifier (LLM + rules + cross-check)

```
Implement code/audit/llm.py and code/audit/intent.py and code/prompts/intent_classifier.md.

llm.py: provider wrapper with: key from env var (ANTHROPIC_API_KEY by default; make provider and model
configurable by env vars LLM_PROVIDER, LLM_MODEL), temperature 0, JSON-only responses, retries with
backoff, disk cache keyed by SHA-256 of (model + prompt) in code/cache/llm_cache.json, and token
accounting per model (calls, input_tokens, output_tokens) saved to code/evaluation/usage_stats.json.
Cached hits must not count as calls. If no key is set, raise a clear error that tells the user to use --no-llm.

intent.py:
 - classify_texts(unique_texts, use_llm) -> {text: {"intent": "DELETE"|"NON_DELETE", "reason": str, "source": "llm"|"rules"}}
 - LLM path: batch ~25 unique texts per call, return strict JSON list. Prompt in code/prompts/intent_classifier.md.
   Definition: DELETE only if the person asks to erase/close/remove their account or personal data.
   NON_DELETE: access/copy/export request, correction, change of details, marketing opt-out only,
   login help, any text saying not to delete or keep the account. Text may be in any language.
 - Rules path (--no-llm): multilingual stems for delete/erase/close/remove in the languages found in
   data_notes.md, plus negation handling ("do not delete", "not asking for deletion", "keep the account").
 - Cross-check: parse system_activity CLASSIFY_REQUEST rows and report, in a printed table, any request
   whose classification disagrees with that signal (link by resource_id appearing in evidence next to the email).
Run both paths over all unique texts; print counts and the NON_DELETE texts; print disagreements between
LLM and rules. Do NOT hardcode any case ID.
```
**Check:** a short list (~10) of NON_DELETE texts, all clearly non-deletion; rules vs LLM disagreements are explainable.

---

## P4 — Evidence parsers → fact store

```
Implement code/audit/facts.py and code/audit/parsers/*.py per docs/02_Architecture.md sections 3 and 7.

Requirements:
- A Fact dataclass and a FactStore with indexes by resource_id, lowercase email, email_hash, user_id,
  phone, and by (system_id, resource_id); fast query: facts_for(identifiers, until=audit_at).
- sql_parser: read the .sql text, parse header comments ("-- Captured at:", "-- Database topology:"),
  execute into sqlite3 ":memory:", iterate every table, emit one Fact per row with normalized fields and
  a category from the table name (print the table-name -> category mapping you chose). Preserve topology
  (primary/failover/read/regional/reporting) as separate systems of record. Handle SQL files that define
  multiple databases or repeated table names by running each file in a fresh connection and tagging table names.
- json_parser: handle every shape listed in data_notes.md (service_exports.profile_lookups, snapshots[],
  records[] ledgers, export manifests/jobs, connector configurations, analytics report). status_code
  404 / result NOT_FOUND / profile null => ABSENT. 200 / FOUND => PRESENT, and record exactly which
  identifier fields are non-null.
- log_parser: key=value regex; handle every log dialect in data_notes.md; map events to facts
  (profile lookups rows/http_status, deletion_marker_check, connector/data-flow state, restore access).
  Count unparsed lines per file and print a summary.
- text_parser: handover .txt pipe format.
- pdf_parser: pdfplumber/pdftotext text -> key/value extraction (customer, user_NN, support_NNN, retention
  dates, hold status, etc.).
- image_parser: pytesseract OCR with disk cache (code/cache/ocr_cache.json); extract key/values the same way.
  Optional: if LLM is enabled and OCR misses expected fields, call the LLM vision fallback using
  code/prompts/vision_extract.md (strict JSON), cached.
- activity.py: turn system_activity rows into Facts with is_claim=True (include activity_id as source_id),
  plus a per-flow and per-backup timeline of CHECK_DATA_FLOW/DISABLE_DATA_FLOW/BLOCK_RESTORE/CHECK_RESTORE_ACCESS/RESTORE_BACKUP events.
- Every Fact's observed_at must use the inner timestamp when present, else the manifest captured_at.
- Normalize: lowercase+strip emails, digits-only phones (keep a '+' flag), sha256 helpers.
Write code/evaluation/test_parsers.py that loads ALL 94 evidence files, prints the fact count per file
and per parser, flags files that produced zero facts, and prints 3 example facts per format.
```
**Check:** zero files with zero facts (or you understand each one); PNG facts contain real fields (names, IDs, statuses).

---

## P5 — State reconstruction + policy engine

```
Implement code/audit/state.py and code/audit/policy.py per docs/02_Architecture.md sections 8 and 9.

policy.py: parse dataset/deletion_rules.csv into a RuleBook. Map each Fact category to its rule and a
required end-state (ABSENT / REDACTED / ANONYMIZED / RETAINED / TOMBSTONE_MIN / FLOW_DISABLED / RESTORE_BLOCKED).
Make the mapping data-driven (a dict in config) and print it. Retention and legal-hold rules must be
decided from evidence facts (audit ledger, retention extract PDF, legal register, console screenshots)
and audit_at, not assumed.

state.py: StateReconstructor(store, activity_timelines).
 - link_resources(identifiers, audit_at): all resources belonging to the user (match by email/hash/
   phone/user_id in facts; LINK_RESOURCE_IDENTITY events; same-row/same-record linkage).
 - resource_state(system, resource, audit_at): latest non-claim fact <= audit_at; otherwise UNKNOWN; use claims only
   for recreation risk (a SYNC_RECORD or RESTORE_BACKUP after the last absent observation while the flow/restore path
   is still enabled/restorable).
 - flow_state(flow_id, audit_at) and backup_state(backup_id, audit_at): latest evidence/claim.
 - evidence selection: for each state return the source_id (file_id, activity_id, or audit_id) that proves it.
Return typed objects: ResourceState(system, resource, category, presence, exposed_identifiers, topology, source_id).
Then implement violations(user_resources, audit_at) -> list of Violation(kind in {REMAINING, EXPOSED_PII,
ACTIVE_FLOW, RESTORE_RISK, RETAINED_MISSING}, system, resource, source_id).
Add a debug command: python3 code/main.py --cases case_05,case_06 --debug that prints, per case, identifiers,
linked resources, states, violations with source IDs. Do not build steps yet.
```
**Check:** `--debug` for sample cases shows plausible violations; compare by eye with `sample_output.csv` steps (findings should match).

---

## P6 — Planner, writer, validator, full run

```
Implement code/audit/planner.py, writer.py and code/main.py per docs/02_Architecture.md sections 10 and 12.

planner.build(case, intent, violations, retained/compliant checks) -> (status, steps):
 - NON_DELETE -> ("NOT_APPLICABLE", [])
 - no violations -> COMPLETE with only VERIFICATION steps; evidence_id = the proving source_id (non-empty).
 - violations -> INCOMPLETE: FINDING steps with evidence_id; REMEDIATION steps with ""; VERIFICATION
   steps with "" for every relevant record per the observed sample pattern (see docs/01 section 3, hypotheses H1/H5).
 - dedupe, sort by (PHASE_ORDER, OP_ORDER, system_id, resource_id), renumber step_no from 1, set state from OP_STATE.
writer: write ./output.csv with csv.writer, header case_id,deletion_status,steps_json, rows in natural case_id
order, steps via json.dumps(separators=(",",":"), ensure_ascii=False). validate() implements every rule in
docs/02 section 12 and raises with a clear message; run validate before declaring success.
main.py CLI: --no-llm, --cases a,b,c, --debug, --dataset-dir, --out, --sample (run on sample_deletion_requests.csv and
write to code/evaluation/sample_predictions.csv instead of root output.csv). Print a progress line every 50 cases
and a final summary (counts by status, validation OK).
Run on the full dataset and on --sample.
```
**Check:** `python3 code/main.py` finishes, prints validation OK, 518 rows.

---

## P7 — Evaluator and the improvement loop

```
Implement code/evaluation/evaluate.py (spec in docs/04_Evaluation_and_Report_Templates.md section 1).
It runs the pipeline on dataset/sample_deletion_requests.csv and compares with dataset/sample_output.csv and prints:
status accuracy; step-level precision/recall/F1 on (phase,system_id,resource_id,operation,state); field-level accuracy
for each of the 7 fields over matched steps; evidence_id accuracy; sequence accuracy (exact ordered match, and a
normalized LCS ratio); per-case exact-match rate; and a ranked list of the worst cases with a readable diff
(missing steps, extra steps, wrong evidence_id, wrong order). Save results to code/evaluation/results_latest.json.

Then run the improvement loop:
1. Run evaluate.py. Take the 3 worst failure categories (not individual cases).
2. For each, open a failing case with --debug, print the raw evidence for the resources involved, and explain the
   root cause in 2 sentences (parsing bug, wrong time filter, wrong evidence choice, wrong policy mapping, wrong ordering).
3. Fix the root cause in general code (no case-specific branches). Re-run evaluate.py. Report before/after metrics.
4. Repeat until status accuracy is 100% on samples and step F1 is as high as you can get; stop when remaining
   failures are explained or time is up.
Log every iteration (what failed, why, what fixed it, metrics before/after) in code/evaluation/iteration_log.md —
I will use it for the evaluation report.
```
**Check:** sample status 32/32; step F1 trending up; iteration log populated.

---

## P8 — Custom tests, reports, README, packaging

```
1. Create at least 3 custom evaluation cases (target 5-6) in code/evaluation/custom_cases/ as Python/Markdown
   (not only CSV): each with a small synthetic mini-dataset or an overlay on the real one, a description, and the
   expected status and steps. Cover: (a) a non-deletion request in a non-English language that mentions the word
   "delete" negatively; (b) request email is an old email and the leftover record only has the old email;
   (c) evidence file captured AFTER audit_at that would change the answer if (wrongly) used; (d) tombstone that still
   contains an email hash; (e) backup restorable vs already blocked; (f) uppercase email in evidence.
   Provide custom_cases/run_custom_cases.py that executes them and prints PASS/FAIL.
2. Write code/evaluation/evaluation_report.md using the template in docs/04 section 2, with real numbers from
   results_latest.json, the custom case results, and the failures/improvements from iteration_log.md.
3. Run the FINAL full-dataset run (python3 code/main.py) once with the intended settings, then generate
   code/evaluation/usage_report.md from usage_stats.json using docs/04 section 3 (fill real model names; leave pricing
   cells as numbers I provide: ask me for input/output price per million tokens if not known).
4. Write README.md (repo root, also included in the zip) using docs/04 section 4.
5. Run the final validator and the packaging checks from docs/05 section 2; produce code.zip WITHOUT dataset/, .venv,
   __pycache__, caches that contain request text, or any nested archive.
Show me the file tree and the validator output.
```
**Check:** all checklist items in `05_Submission_and_Interview.md` pass.

---

## Helper prompts

### H1 — Debug one failing case
```
Case <case_id> disagrees with the expected answer (only for sample cases, using sample_output.csv for comparison).
Print: request, identifiers, linked resources, the facts you used (source_id, observed_at, system, resource, presence,
topology), the facts you ignored because they are after audit_at, the violations, and the final steps next to the
expected steps. Explain the root cause and propose the smallest GENERAL fix. Do not special-case this case.
```

### H2 — Hidden-test robustness review
```
Review the code for generalization to unseen cases (the grader uses hidden answers on the 518 real cases). List every
place where behaviour depends on a specific ID format, file name, date, or the 32 sample cases. Propose fixes. Then
run the pipeline on a shuffled copy of deletion_requests.csv and confirm identical output rows.
```

### H3 — Token-saving audit
```
Print total LLM calls, input/output tokens by model for the last run, cache hit rate, and the biggest prompts. Suggest
two concrete ways to cut tokens without changing outputs (bigger batches, dedupe, shorter instructions), implement them,
and show before/after.
```

### H4 — Interview rehearsal
```
Act as the AI judge. Ask me 10 hard questions about this solution (architecture, time-cutoff rule, NOT_APPLICABLE logic,
policy mapping, evidence choice, replication drift, evaluation, failures, cost, AI usage). After each of my answers, grade
it and point to the exact file/function that supports or contradicts my answer.
```
