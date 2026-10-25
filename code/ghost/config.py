"""Paths, environment settings and fixed contract constants.

Everything that the output contract fixes (operation order, allowed states,
status mapping) lives here so no other module hardcodes it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"
CACHE_DIR = REPO_ROOT / "cache"
OUTPUT_CSV = REPO_ROOT / "output.csv"

REQUESTS_CSV = DATASET_DIR / "deletion_requests.csv"
SAMPLE_REQUESTS_CSV = DATASET_DIR / "sample_deletion_requests.csv"
SAMPLE_OUTPUT_CSV = DATASET_DIR / "sample_output.csv"
IDENTITIES_CSV = DATASET_DIR / "user_identities.csv"
AUDIT_LOG_CSV = DATASET_DIR / "user_audit_log.csv"
ACTIVITY_CSV = DATASET_DIR / "system_activity.csv"
RULES_CSV = DATASET_DIR / "deletion_rules.csv"
EVIDENCE_MANIFEST_CSV = DATASET_DIR / "evidence_files.csv"

TABLES_DB = CACHE_DIR / "tables.sqlite"
LLM_CACHE_DIR = CACHE_DIR / "llm"
RUN_LOG = CACHE_DIR / "run.log"
REVIEW_JSONL = CACHE_DIR / "review.jsonl"
USAGE_JSON = CACHE_DIR / "usage.json"

OUTPUT_COLUMNS = ("case_id", "deletion_status", "steps_json")

# --- Output contract -------------------------------------------------------

PHASE_ORDER = ("FINDING", "REMEDIATION", "VERIFICATION")

# Within-phase sort order, exactly as listed in problem_statement.md.
OPERATION_ORDER: dict[str, tuple[str, ...]] = {
    "FINDING": (
        "REPORT_REMAINING_RECORD",
        "REPORT_EXPOSED_PII",
        "REPORT_ACTIVE_DATA_FLOW",
        "REPORT_RESTORE_RISK",
    ),
    "REMEDIATION": (
        "DISABLE_DATA_FLOW",
        "BLOCK_RESTORE",
        "DELETE_RECORD",
        "REDACT_RECORD",
        "ANONYMIZE_RECORD",
    ),
    "VERIFICATION": (
        "VERIFY_RECORD_ABSENT",
        "VERIFY_RECORD_PRESENT",
        "VERIFY_RECORD_REDACTED",
        "VERIFY_RECORD_ANONYMIZED",
        "VERIFY_DATA_FLOW_DISABLED",
        "VERIFY_RESTORE_BLOCKED",
    ),
}

OPERATION_STATE: dict[str, str] = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

STATUSES = ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE")

# Reported workflow status -> the worker result that usually accompanies it.
# Used only to rank linkage candidates, never as proof of state.
REPORTED_TO_RESULT = {
    "COMPLETE": "SUCCESS",
    "PARTIALLY_COMPLETE": "PARTIAL",
    "NOT_STARTED": "FAILED",
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings read from the environment once at start-up."""

    openai_api_key: str | None
    model: str
    offline: bool

    @classmethod
    def from_env(cls, offline: bool = False) -> "Settings":
        _load_dotenv(REPO_ROOT / ".env")
        key = os.environ.get("OPENAI_API_KEY") or None
        model = os.environ.get("GHOST_MODEL") or "gpt-4.1-mini"
        return cls(openai_api_key=key, model=model, offline=offline or key is None)


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, existing env vars win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
