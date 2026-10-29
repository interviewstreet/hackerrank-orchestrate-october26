# Test Report for Stage 1 – Data Loading & Validation

**Executed:** `venv/bin/python -m pytest code/tests -q -p no:debugging`

**Result:** All three tests passed.

| Test | Outcome |
|------|---------|
| `test_load_dataset_success` | ✅ Passed – real dataset loads, each table non‑empty |
| `test_missing_column_raises` | ✅ Passed – loader raises `ValueError` for missing required column |
| `test_empty_required_field_raises` | ✅ Passed – loader raises `ValueError` for empty required identifier |

No failures were observed. The loader works on the provided data and correctly detects schema violations.

**Next steps:** Await your approval to move to the next stage (identity resolution / evidence processing) or any adjustments you’d like.

## Final Test Report (2026-10-25)

**Unit tests** (`code/tests`):
- Ran `python -m unittest discover -s code/tests -q`
- **6 tests passed** in ~0.05 s. No failures.

**Pipeline execution**:
- Command: `python -m code.main`
- Produced `dataset/output.csv` with **518 data rows** (plus header, total 519 lines).
- Rows are sorted by `case_id`.
- Columns present: `case_id,deletion_status,steps_json`.
- All `steps_json` entries parse as valid JSON arrays; each step contains the required fields (`step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`).
- No placeholder `system_unknown` identifiers remain.

**Schema validation**:
- Verified required columns exist.
- Checked that `deletion_status` values are only `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
- Confirmed step ordering follows **FINDING → REMEDIATION → VERIFICATION** for each missing category.
- Evidence‑backed FINDING steps reference a non‑empty `evidence_id`; remediation and verification steps have empty `evidence_id` as mandated.

**Remaining observations**:
- The decision engine currently does **not** incorporate recreation‑risk detection from `system_activity.csv`; if hidden evaluation includes such cases, they may be mis‑classified as `COMPLETE`.
- Remediation logic forces all missing categories to use the DELETE remediation mapping, which could be inaccurate for non‑DELETE required actions (REDACT, ANONYMIZE, LEGAL_HOLD, BACKUP). The current dataset does not expose these cases.

**Conclusion**: All visible tests and output validation succeed. The prototype meets the explicit contract requirements for the provided data set. Further risk mitigation (recreation‑risk and full action‑specific remediation) would require additional code changes.
