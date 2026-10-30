"""Paths (resolved from the repository root) and environment settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = CODE_DIR.parent
DEFAULT_DATASET_DIR = REPO_ROOT / "dataset"
DEFAULT_OUTPUT = REPO_ROOT / "output.csv"
CACHE_DIR = CODE_DIR / "cache"
PROMPTS_DIR = Path(__file__).resolve().parent / "llm" / "prompts"

# Process exit codes of code/main.py (documented in README.md)
EXIT_OK = 0
EXIT_INPUT_MISSING = 1          # a dataset input file or directory does not exist
EXIT_INVALID_OUTPUT = 2         # output.csv failed contract validation
EXIT_BUDGET_EXCEEDED = 3        # LLM spend cap reached with GDA_BUDGET_ON_EXCEED=abort
EXIT_UNVERIFIED_EVIDENCE = 4    # a COMPLETE verdict rests on visual evidence that could not be read


@dataclass(frozen=True)
class DatasetPaths:
    root: Path
    requests: Path

    @property
    def identities(self) -> Path:
        return self.root / "user_identities.csv"

    @property
    def audit_log(self) -> Path:
        return self.root / "user_audit_log.csv"

    @property
    def activity(self) -> Path:
        return self.root / "system_activity.csv"

    @property
    def rules(self) -> Path:
        return self.root / "deletion_rules.csv"

    @property
    def manifest(self) -> Path:
        return self.root / "evidence_files.csv"

    @property
    def sample_requests(self) -> Path:
        return self.root / "sample_deletion_requests.csv"

    @property
    def sample_output(self) -> Path:
        return self.root / "sample_output.csv"

    @property
    def eval_requests(self) -> Path:
        return self.root / "deletion_requests.csv"

    def required(self) -> list[Path]:
        """Inputs every run needs (the request file is checked separately)."""
        return [self.identities, self.audit_log, self.activity, self.rules, self.manifest]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


BACKENDS = ("replay", "claude_cli", "anthropic", "openai", "ollama", "offline")


def llm_backend() -> str:
    return env("GDA_LLM_BACKEND", "replay").strip().lower()


def budget_usd() -> float:
    try:
        return float(env("GDA_BUDGET_USD", "3.00"))
    except ValueError:
        return 3.0


def _flag(name: str, default: bool) -> bool:
    v = env(name, "1" if default else "0").strip().lower()
    return v not in {"0", "false", "no", "off", ""}


def vision_llm() -> bool:
    """GDA_VISION (default on): read screenshots/PDFs with the vision model (cache or live). 0 = never call it."""
    return _flag("GDA_VISION", True)


def vision_grounding() -> bool:
    """GDA_VISION_GROUNDING (default on): drop vision-model records that the OCR text of the image does not show."""
    return _flag("GDA_VISION_GROUNDING", True)


def vision_ocr_fallback() -> bool:
    """GDA_VISION_OCR_FALLBACK (default on): read an image by OCR when no vision-model result exists."""
    return _flag("GDA_VISION_OCR_FALLBACK", True)
