## Submission Summary (2026-10-25)

- **All unit tests** (`code/tests`) **passed** (6 tests).
- **Pipeline execution** (`python -m code.main`) completed successfully and wrote `dataset/output.csv` with **518 rows**.
- **Output validation**:
  - Correct columns `case_id,deletion_status,steps_json`.
  - Rows sorted by `case_id`.
  - `deletion_status` values conform to contract (`COMPLETE`, `INCOMPLETE`, `NOT_APPLICABLE`).
  - `steps_json` is a valid JSON array; each step contains required fields (`step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`).
  - FINDING steps reference real `evidence_id`; REMEDIATION and VERIFICATION steps have empty `evidence_id` as required.
- **Decision engine**:
  - Implements full classification logic per **AGENTS.md §6.3**.
  - Added recreation‑risk detection using `system_activity.csv` (SYNC/EXPORT/RESTORE) and corresponding risk‑mitigation evidence.
- **Remediation generation**:
  - Extracts real `system_id` from evidence file paths; no `system_unknown` placeholders remain.
- **Evaluation artifacts**:
  - `evaluation/evaluation_report.md` and `evaluation/usage_report.md` created with test outcomes and basic usage stats.
- **Logging**:
  - Final per‑turn entry appended to `log.txt` with required `tool=` and `model=` fields.

### Remaining minor risks
1. **Recreation‑risk coverage** – currently limited to activity types listed in the dataset; if other risk vectors exist they would be classified as `INCOMPLETE` by default.
2. **Cost estimation** – usage report contains approximate token counts; precise cost calculation would require model pricing details.
3. **No further automated checks** – manual review of a random sample of cases is advisable before final submission.

The repository is now frozen and ready for submission. No further changes will be made without explicit permission.
