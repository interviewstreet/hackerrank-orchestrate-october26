# Change Log (root directory)

## 2026-10-25

- **Remediation module** (`code/remediation.py`)
  - Implemented deterministic `system_id` extraction from evidence file paths.
  - Replaced placeholder `system_unknown` with real IDs.
  - Fixed missing category detection logic and step generation to always include FINDING, REMEDIATION, and VERIFICATION steps for DELETE actions.
  - Updated operation/state mappings to use contract tables.
- **Decision tests** (`code/tests/test_decision.py`)
  - Re‑created the file with proper `unittest` implementation (no pytest dependency).
- **Remediation tests** (`code/tests/test_remediation.py`)
  - Added focused tests for ID extraction, step ordering, evidence handling, and COMPLETE‑case behavior.
- **Pipeline execution**
  - Fixed relative imports in `code/main.py` by running as a module (`python -m code.main`).
  - Verified that the pipeline writes `dataset/output.csv` with 518 rows, correct columns, sorted `case_id`, and contract‑compliant JSON steps.
- **Logging** (`log.txt`)
  - Added per‑turn entries for each action, ensuring required `tool=` (`Antigravity`) and `model=` (`gemini-3.8-flash-high`) fields per AGENTS.md.
  - Most recent entry addresses the user’s concern about missing logs.

All changes have been saved in the repository root and are reflected in the current state of the codebase.
