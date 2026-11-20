#!/usr/bin/env python3
"""Offline October submission preparation. Python 3.10+, standard library only.

Only README.md and eligible code/ files enter the ZIP. No build directories are
excluded by generic names (lib, bin, dist and custom dataset fixtures survive).
This checks format, not prediction correctness or transcript authenticity.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
import uuid
import zipfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

if sys.version_info < (3, 10):
    print("Orchestrate requires Python 3.10 or newer. Try python3.10 (or py -3.10 on Windows).", file=sys.stderr)
    sys.exit(2)

CLI_VERSION = "1.0.0"
CONTRACT_ID = "orchestrate-october26-v1"
# Release prerequisite: organizers must confirm DataSetFile.upload_limit per slot.
UPLOAD_LIMITS = {"code.zip": None, "output.csv": None, "log.txt": None}
ARTIFACTS = frozenset(UPLOAD_LIMITS)
REPORTS = ("README.md", "code/evaluation/evaluation_report.md", "code/evaluation/usage_report.md")
HEADERS = ["case_id", "deletion_status", "steps_json"]
FIELDS = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
# Public problem-statement table order is significant.
OPERATIONS = [
    ("FINDING", "REPORT_REMAINING_RECORD", "PRESENT"),
    ("FINDING", "REPORT_EXPOSED_PII", "PRESENT"),
    ("FINDING", "REPORT_ACTIVE_DATA_FLOW", "ACTIVE"),
    ("FINDING", "REPORT_RESTORE_RISK", "ACTIVE"),
    ("REMEDIATION", "DISABLE_DATA_FLOW", "DISABLED"),
    ("REMEDIATION", "BLOCK_RESTORE", "BLOCKED"),
    ("REMEDIATION", "DELETE_RECORD", "ABSENT"),
    ("REMEDIATION", "REDACT_RECORD", "REDACTED"),
    ("REMEDIATION", "ANONYMIZE_RECORD", "ANONYMIZED"),
    ("VERIFICATION", "VERIFY_RECORD_ABSENT", "ABSENT"),
    ("VERIFICATION", "VERIFY_RECORD_PRESENT", "PRESENT"),
    ("VERIFICATION", "VERIFY_RECORD_REDACTED", "REDACTED"),
    ("VERIFICATION", "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED"),
    ("VERIFICATION", "VERIFY_DATA_FLOW_DISABLED", "DISABLED"),
    ("VERIFICATION", "VERIFY_RESTORE_BLOCKED", "BLOCKED"),
]
PRUNE = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "site-packages",
         "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__MACOSX"}
CREDENTIALS = {"credentials.json", "credentials.ini", ".netrc", "_netrc", ".npmrc", ".pypirc",
               "id_rsa", "id_ed25519", ".aws", ".ssh"}
ARCHIVES = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}
STATE = ".orchestrate-state.json"
LOCK = ".orchestrate.lock"


class OperationalError(Exception):
    """Expected filesystem/preparation failure (exit 3)."""


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    path: str
    message: str
    hint: str
    row: int | None = None


@dataclass(frozen=True)
class PackageFile:
    source: Path
    archive_name: str


@dataclass
class CheckResult:
    findings: list = field(default_factory=list)
    package_files: list = field(default_factory=list)
    snapshots: dict = field(default_factory=dict)
    expected_ids: set | None = None
    totals: Counter = field(default_factory=Counter)
    occurrences: Counter = field(default_factory=Counter)
    excluded: list = field(default_factory=list)
    excluded_count: int = 0

    def add(self, code, path, message, hint, severity="error", row=None):
        self.totals[severity] += 1
        self.occurrences[code] += 1
        if self.occurrences[code] <= 5:
            self.findings.append(Finding(code, severity, str(path), message, hint, row))


def resolve_repo_root():
    return Path(__file__).resolve().parent


def special(path):
    s = path.lstat()
    return stat.S_ISLNK(s.st_mode) or bool(getattr(s, "st_file_attributes", 0) & 0x400)


def safe_path(path, root, directory=False):
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current /= part
        if special(current):
            raise ValueError("Symlinks and junctions are unsupported; replace with a local regular file/directory.")
    mode = path.lstat().st_mode
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise ValueError("Expected a regular directory." if directory else "Expected a regular file.")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escapes the checkout.")


def identity(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode)


def read_bytes(path, root, result=None):
    safe_path(path, root)
    before = identity(path)
    if result is not None and path in result.snapshots and result.snapshots[path] != before:
        raise OperationalError(f"Input changed: {path}. Finish generating files and rerun prepare.")
    data = path.read_bytes()
    if identity(path) != before:
        raise OperationalError(f"Input changed while reading: {path}. Finish writing and rerun.")
    if result is not None:
        result.snapshots[path] = before
    return data


def archive_payload(data):
    return (data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\x1f\x8b", b"7z\xbc\xaf\x27\x1c", b"Rar!"))
            or data[257:262] == b"ustar")


def text_file(path, root, result, code):
    try:
        data = read_bytes(path, root, result)
        if b"\0" in data or archive_payload(data[:512]):
            raise ValueError("Expected UTF-8 text, found binary/archive content.")
        text = data.decode("utf-8-sig")
        if not text.strip():
            raise ValueError("File is empty or whitespace-only.")
        return text
    except (OSError, ValueError) as exc:
        hints = {
            "OUTPUT_UNREADABLE": "Generate final predictions at root output.csv, not dataset/output.csv; use readable UTF-8 CSV.",
            "TRANSCRIPT_UNREADABLE": "Use the actual root log.txt recorded by your coding agent; check AGENTS.md logging and never reconstruct turns.",
            "REPORT_MISSING": "Write your actual report (or README setup/run instructions) as nonempty UTF-8 at this canonical path.",
            "REFERENCE_INVALID": "Restore the public dataset/deletion_requests.csv from this starter checkout.",
            "CHECKOUT_INVALID": "Restore AGENTS.md and keep orchestrate.py at the starter checkout root.",
        }
        result.add(code, path.relative_to(root), str(exc) if not isinstance(exc, UnicodeError) else "Not UTF-8 text.",
                   hints.get(code, "Provide the required readable UTF-8 file at this exact path."))
        return None


def excluded_name(name):
    low = name.lower()
    return (low in PRUNE or low in CREDENTIALS or low == ".ds_store" or low.startswith("._")
            or low.endswith((".pyc", ".pyo", ".pem", ".key"))
            or (low == ".env" or low.startswith(".env.")) and low not in {".env.example", ".env.sample"})


def collect_package_files(root, result):
    names = set()

    def exclude(path):
        result.excluded_count += 1
        if len(result.excluded) < 5:
            result.excluded.append(path.relative_to(root).as_posix())

    def visit(path):
        if excluded_name(path.name):
            exclude(path)
            return
        try:
            if special(path):
                raise ValueError("Selected symlink/junction; replace with a local regular path.")
            if path.is_dir():
                safe_path(path, root, directory=True)
                if (path / "pyvenv.cfg").exists() or (path / "pyvenv.cfg").is_symlink():
                    exclude(path)
                    return
                for child in sorted(path.iterdir()):
                    visit(child)
                return
            safe_path(path, root)
            name = path.relative_to(root).as_posix()
            parts = PurePosixPath(name).parts
            # Reject Windows-unsafe names as well when running on Unix.
            if (PurePosixPath(name).is_absolute() or any(p in {".", ".."} for p in parts)
                    or any(re.search(r'[<>:"\\|?*\x00-\x1f]', p) or p.endswith((".", " "))
                           or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?", p) for p in parts)):
                raise ValueError("Unsafe cross-platform archive name; rename this path.")
            normalized = unicodedata.normalize("NFC", name).casefold()
            if normalized in names:
                raise ValueError("Archive path duplicates or case-collides with another selected path; rename it.")
            names.add(normalized)
            before = identity(path)
            with path.open("rb") as source:
                signature = source.read(512)
            if identity(path) != before:
                raise OperationalError(f"Input changed: {path}. Rerun after writing finishes.")
            result.snapshots[path] = before
            if path.suffix.lower() in ARCHIVES or archive_payload(signature):
                result.add("CODE_NESTED_ARCHIVE", name, "Nested archive detected.", "Move this archive outside code/; submit source files directly.")
            result.package_files.append(PackageFile(path, name))
        except (OSError, ValueError) as exc:
            result.add("CODE_UNSAFE_PATH", path.relative_to(root), str(exc), "Use readable regular files within this checkout.")

    visit(root / "README.md")
    visit(root / "code")
    result.package_files.sort(key=lambda p: p.archive_name)
    if not any(p.archive_name.startswith("code/") for p in result.package_files):
        result.add("CODE_EMPTY", "code/", "No eligible files found.", "Place your solution and reports under code/.")


def csv_records(path, root, result, code):
    text = text_file(path, root, result, code)
    if text is None:
        return None
    try:
        # Standard quoted multiline cells supported; blank records are ignored.
        return [row for row in csv.reader(io.StringIO(text, newline=""), strict=True) if row]
    except csv.Error:
        result.add(code, path.relative_to(root), "Malformed CSV quoting or field size exceeds parser capacity.",
                   "Regenerate standard CSV with properly quoted multiline/JSON cells.")
        return None


def load_expected_case_ids(root, result):
    path = root / "dataset/deletion_requests.csv"
    rows = csv_records(path, root, result, "REFERENCE_INVALID")
    if rows is None:
        return None
    if not rows or rows[0].count("case_id") != 1 or len(set(rows[0])) != len(rows[0]):
        result.add("REFERENCE_INVALID", path.relative_to(root), "Missing or duplicate reference headers.", "Restore the public request dataset from the starter checkout.")
        return None
    index = rows[0].index("case_id")
    ids = [row[index] for row in rows[1:] if len(row) == len(rows[0])]
    if len(ids) != len(rows) - 1 or not ids or any(not x.strip() for x in ids) or len(ids) != len(set(ids)):
        result.add("REFERENCE_INVALID", path.relative_to(root), "Reference IDs are empty, duplicated, or rows have wrong cell counts.", "Restore the public request dataset; coverage could not be checked.")
        return None
    return set(ids)


def strict_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def reject_constant(value):
    raise ValueError("nonstandard JSON constant")


def check_steps(raw, status, path, row, result):
    try:
        steps = json.loads(raw, object_pairs_hook=strict_object, parse_constant=reject_constant)
    except (ValueError, RecursionError):
        result.add("OUTPUT_JSON", path, "steps_json is not strict JSON (including duplicate keys/NaN).", "Serialize a JSON array with standard JSON values.", row=row)
        return
    if not isinstance(steps, list):
        result.add("OUTPUT_JSON_ARRAY", path, "steps_json must be an array.", "Use [] for NOT_APPLICABLE.", row=row)
        return
    if status == "NOT_APPLICABLE" and steps:
        result.add("OUTPUT_NOT_APPLICABLE", path, "NOT_APPLICABLE has nonempty steps.", "Use an empty array for a non-deletion request.", row=row)
    previous = None
    for i, step in enumerate(steps, 1):
        if (not isinstance(step, dict) or set(step) != FIELDS or type(step.get("step_no")) is not int
                or any(not isinstance(step.get(k), str) for k in FIELDS - {"step_no"})):
            result.add("OUTPUT_STEP_FIELDS", path, f"Step {i} has incorrect fields or types.", "Use exactly the seven documented fields; step_no is an integer, others strings.", row=row)
            continue
        if step["step_no"] != i:
            result.add("OUTPUT_STEP_NUMBER", path, f"Step {i} is not numbered consecutively.", "Number steps from 1 in their intended order.", row=row)
        triple = (step["phase"], step["operation"], step["state"])
        if triple not in OPERATIONS:
            result.add("OUTPUT_OPERATION", path, f"Step {i} has incompatible phase/operation/state.", "Follow the public Allowed Operations table (VERIFY_DATA_FLOW_DISABLED uses DISABLED).", row=row)
            continue
        order = (OPERATIONS.index(triple), step["system_id"], step["resource_id"])
        if previous is not None and order < previous:
            result.add("OUTPUT_STEP_ORDER", path, f"Step {i} violates phase/operation/system/resource order.", "Follow the public table order, then ascending system_id and resource_id.", row=row)
        previous = order
        if status == "COMPLETE" and step["phase"] != "VERIFICATION":
            result.add("OUTPUT_COMPLETE_PHASE", path, "COMPLETE contains findings/remediation.", "COMPLETE permits verification steps only.", row=row)


def check_output(path, root, expected_ids, result):
    rows = csv_records(path, root, result, "OUTPUT_UNREADABLE")
    if rows is None:
        return
    relative = path.relative_to(root)
    if not rows or rows[0] != HEADERS:
        result.add("OUTPUT_HEADER", relative, "Incorrect ordered CSV header.", "Use exactly case_id,deletion_status,steps_json, with no duplicate columns.")
        return
    ids = []
    for number, cells in enumerate(rows[1:], 2):
        if len(cells) != 3:
            result.add("OUTPUT_CELLS", relative, "Record has missing/extra cells.", "Quote JSON and multiline cells with a standard CSV writer.", row=number)
            continue
        case_id, status, raw = cells
        ids.append(case_id)
        if not case_id.strip():
            result.add("OUTPUT_BLANK_ID", relative, "Blank case ID.", "Use the exact public request ID.", row=number)
        if status not in {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}:
            result.add("OUTPUT_STATUS", relative, "Unknown deletion_status.", "Use COMPLETE, INCOMPLETE or NOT_APPLICABLE exactly.", row=number)
        check_steps(raw, status, relative, number, result)
    duplicates = {k for k, count in Counter(ids).items() if count > 1}
    if duplicates:
        result.add("OUTPUT_DUPLICATE_IDS", relative, f"{len(duplicates)} duplicated IDs.", "Produce one row per public request.")
    if expected_ids is not None:
        for code, values, label in [("OUTPUT_MISSING_IDS", expected_ids - set(ids), "Missing"),
                                     ("OUTPUT_UNKNOWN_IDS", set(ids) - expected_ids, "Unknown")]:
            if values:
                # IDs are untrusted input; bound and escape examples in terminal output.
                sample = ", ".join(ascii(x[:80]) for x in sorted(values)[:5])
                result.add(code, relative, f"{label} {len(values)} IDs: {sample}.", "Generate exactly one row for every ID in dataset/deletion_requests.csv.")


def check_transcript(path, root, result):
    text = text_file(path, root, result, "TRANSCRIPT_UNREADABLE")
    if text is None:
        return
    # Ignore fenced/indented code and blockquotes, including quoted format examples.
    lines = text.splitlines()
    structural = []
    fence = None
    for line in lines:
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if match:
            token = match[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            structural.append(False)
            continue
        structural.append(fence is None and not re.match(r"^( {4}|\t| {0,3}>)", line))
    starts = []
    for i, line in enumerate(lines):
        if not structural[i]:
            continue
        match = re.match(r"^##\s+\[?(\d{4}-\d{2}-\d{2}[T ][0-9:.+Z-]+)(?:\]|\s)\s*(.*)$", line)
        if match:
            try:
                datetime.fromisoformat(match[1].replace("Z", "+00:00"))
                starts.append((i, "SESSION START" in match[2]))
            except ValueError:
                pass
    valid = incomplete = sessions = 0
    for n, (start, session) in enumerate(starts):
        if session:
            sessions += 1
            continue
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        sections = []
        decorated = False
        for i in range(start + 1, end):
            if not structural[i]:
                continue
            line = lines[i].strip()
            clean = line.strip("* ")
            if re.fullmatch(r"User Prompt(?: \(verbatim[^)]*\))?:", clean):
                heading = "User Prompt"
            elif clean in {"Agent Response Summary:", "Actions:", "Context:"}:
                heading = clean[:-1]
            else:
                continue
            decorated |= clean != line
            sections.append((heading, i))
        if [s[0] for s in sections] != ["User Prompt", "Agent Response Summary", "Actions", "Context"]:
            incomplete += 1
            continue
        bodies = ["\n".join(lines[i + 1:sections[j + 1][1] if j < 3 else end]).strip()
                  for j, (_, i) in enumerate(sections)]
        if not all(bodies):
            incomplete += 1
            continue
        valid += 1
        if decorated:
            result.add("TRANSCRIPT_DECORATED", path.relative_to(root), "Decorated section headings recognized.", "Use the plain AGENTS.md heading format in future turns.", "warning")
        context = bodies[-1]
        if any(not re.search(rf"(?m)^{key}=(?!\s*$|unknown\s*$|<|\[|exact_|your_|AI\s*$|custom:)[^\n]+", context, re.I)
               for key in ("tool", "model")):
            result.add("TRANSCRIPT_METADATA", path.relative_to(root), "Context lacks populated harness/model metadata or has placeholders.", "Record actual runtime metadata in future turns; do not guess or rewrite history.", "warning")
    if not valid:
        result.add("TRANSCRIPT_SESSION_ONLY" if sessions and not incomplete else "TRANSCRIPT_FORMAT", path.relative_to(root),
                   "No dated, structurally complete conversation turn found.", "Check real coding-agent logging against AGENTS.md. Never reconstruct a conversation.")
    elif incomplete:
        result.add("TRANSCRIPT_INCOMPLETE", path.relative_to(root), f"{incomplete} incomplete dated turns.", "Review logging; at least one structured turn was recognized.", "warning")


def run_checks(root):
    result = CheckResult()
    text_file(root / "AGENTS.md", root, result, "CHECKOUT_INVALID")
    collect_package_files(root, result)
    for report in REPORTS:
        text_file(root / report, root, result, "REPORT_MISSING")
        legacy = root / "evaluation" / Path(report).name
        if report.startswith("code/") and not (root / report).exists() and legacy.is_file():
            result.add("REPORT_LOCATION", legacy.relative_to(root), "Report exists only at the legacy location.", f"Place your actual report at {report}; it is not relocated automatically.")
    packaged = {p.archive_name for p in result.package_files}
    for report in REPORTS:
        already_invalid = any(f.code == "REPORT_MISSING" and f.path == report for f in result.findings)
        if report not in packaged and not already_invalid:
            result.add("REPORT_NOT_PACKAGED", report, "Required report is absent from the eligible package plan.",
                       "Keep this report in the canonical location, outside excluded environments/directories.")
    result.expected_ids = load_expected_case_ids(root, result)
    check_output(root / "output.csv", root, result.expected_ids, result)
    check_transcript(root / "log.txt", root, result)
    if any(v is None for v in UPLOAD_LIMITS.values()):
        result.add("LIMITS_UNCONFIRMED", "submission/", "Organizer upload limits have not been supplied; size acceptance is unchecked.",
                   "Release prerequisite: confirm each event DataSetFile.upload_limit; the server remains authoritative.", "warning")
    return result


def assert_unchanged(root, result):
    for path, original in result.snapshots.items():
        try:
            safe_path(path, root)
            if identity(path) == original:
                continue
        except (OSError, ValueError):
            pass
        raise OperationalError(f"Input changed/disappeared: {path}. Finish writing files, then rerun prepare.")


def write_code_zip(plan, destination, root, result):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in plan:
            data = read_bytes(item.source, root, result)
            info = zipfile.ZipInfo.from_file(item.source, item.archive_name, strict_timestamps=False)
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)


def validate_staged_bundle(stage, result):
    with zipfile.ZipFile(stage / "code.zip") as archive:
        names = archive.namelist()
        if names != [p.archive_name for p in result.package_files] or archive.testzip() is not None:
            raise OperationalError("Staged ZIP verification failed; previous submission preserved.")
        for report in REPORTS:
            if not archive.read(report).decode("utf-8-sig").strip():
                raise OperationalError("Required staged ZIP report is empty.")
    checked = CheckResult()
    check_output(stage / "output.csv", stage, result.expected_ids, checked)
    check_transcript(stage / "log.txt", stage, checked)
    if checked.totals["error"]:
        raise OperationalError("Staged CSV/transcript verification failed; rerun after inputs stop changing.")
    for name, limit in UPLOAD_LIMITS.items():
        if limit is not None and (stage / name).stat().st_size > limit:
            raise OperationalError(f"Staged {name} exceeds the configured {limit}-byte upload limit.")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bundle_hashes(directory):
    if special(directory) or not directory.is_dir() or {p.name for p in directory.iterdir()} != ARTIFACTS:
        raise OperationalError(f"Refusing unknown/modified bundle: {directory}. Move it aside manually.")
    for name in ARTIFACTS:
        safe_path(directory / name, directory)
    return {name: digest(directory / name) for name in sorted(ARTIFACTS)}


def write_state(root, state):
    path = root / STATE
    temporary = root / (STATE + "." + uuid.uuid4().hex)
    try:
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inspect_publication(root):
    state_path = root / STATE
    state = None
    if state_path.exists() or state_path.is_symlink():
        safe_path(state_path, root)
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise OperationalError(f"Unreadable {state_path}; preserve artifacts and inspect bookkeeping manually.") from exc
        if not isinstance(state, dict) or state.get("owner") != CONTRACT_ID or state.get("phase") != "ready":
            raise OperationalError(f"Interrupted/unknown publication: inspect {state_path}. "
                                   "Follow docs/submission_cli.md recovery; do not delete backups blindly.")
    leftovers = sorted(p for p in root.iterdir() if p.name.startswith((".orchestrate-stage-", ".orchestrate-backup-", STATE + ".")))
    if leftovers:
        raise OperationalError("Interrupted preparation paths: " + ", ".join(str(p) for p in leftovers[:5])
                               + ". Inspect these and follow docs/submission_cli.md recovery before retrying.")
    destination = root / "submission"
    if destination.exists() or destination.is_symlink():
        if state is None or bundle_hashes(destination) != state.get("hashes"):
            raise OperationalError(f"Refusing unknown/modified {destination}; move it aside manually before preparing.")
    elif state is not None:
        raise OperationalError(f"{destination} is missing but bookkeeping exists at {state_path}; follow recovery instructions.")
    return state


@contextmanager
def preparation_lock(root):
    path = root / LOCK
    token = uuid.uuid4().hex
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise OperationalError(f"Preparation lock exists: {path}. If no prepare is running, inspect recovery instructions before removing this stale lock.") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as lock:
            lock.write(token)
        yield
    finally:
        if path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8") == token:
            path.unlink()


def publish_bundle(stage, root, previous):
    destination = root / "submission"
    backup = root / (".orchestrate-backup-" + uuid.uuid4().hex)
    hashes = bundle_hashes(stage)
    # Journal before any directory rename. Interrupted transactions are never auto-deleted.
    journal = {"owner": CONTRACT_ID, "phase": "publishing", "stage": stage.name,
               "backup": backup.name if previous else None, "previous": previous, "hashes": hashes}
    write_state(root, journal)
    moved_previous = published = False
    try:
        if previous:
            destination.rename(backup)
            moved_previous = True
        stage.rename(destination)
        published = True
        write_state(root, {"owner": CONTRACT_ID, "phase": "ready", "hashes": hashes})
    except OSError as exc:
        try:
            if published:
                destination.rename(stage)
            if moved_previous:
                backup.rename(destination)
            if previous:
                write_state(root, previous)
            else:
                (root / STATE).unlink()
        except OSError as rollback:
            raise OperationalError(f"Publication and rollback failed. Preserve {backup}, {stage}, {destination}, and {root / STATE}; follow recovery instructions.") from rollback
        raise OperationalError("Publication failed; previous bundle restored. Check permissions/disk space and retry.") from exc
    if moved_previous:
        # Only remove the exact known bundle moved by this run.
        if bundle_hashes(backup) != previous["hashes"]:
            raise OperationalError(f"Backup changed: preserve and inspect {backup} before retrying.")
        shutil.rmtree(backup)


def prepare(root):
    with preparation_lock(root):
        previous = inspect_publication(root)
        result = run_checks(root)
        print_results(result)
        if result.totals["error"]:
            print("No new submission bundle was published.")
            return 1
        stage = Path(tempfile.mkdtemp(prefix=".orchestrate-stage-", dir=root))
        try:
            write_code_zip(result.package_files, stage / "code.zip", root, result)
            for name in ("output.csv", "log.txt"):
                (stage / name).write_bytes(read_bytes(root / name, root, result))
            validate_staged_bundle(stage, result)
            assert_unchanged(root, result)
            # Recheck destination ownership just before mutating it.
            if previous and bundle_hashes(root / "submission") != previous["hashes"]:
                raise OperationalError("Previous bundle changed during preparation; no publication attempted.")
            if not previous and ((root / "submission").exists() or (root / "submission").is_symlink()):
                raise OperationalError("An unknown submission/ appeared during preparation; move it aside manually.")
            publish_bundle(stage, root, previous)
        finally:
            # A publishing journal means recovery needs the remaining paths intact.
            state_path = root / STATE
            pending = state_path.exists() and json.loads(state_path.read_text(encoding="utf-8")).get("phase") == "publishing"
            if stage.exists() and not pending:
                shutil.rmtree(stage)
        print("Prepared submission files. Local format checks passed" + (f" with {result.totals['warning']} warning(s)." if result.totals['warning'] else "."))
        for label, name in (("Code upload", "code.zip"), ("Predictions upload", "output.csv"), ("Chat transcript", "log.txt")):
            path = root / "submission" / name
            print(f"{label:20} -> {path} ({path.stat().st_size:,} bytes)")
        print(f"Code ZIP: {len(result.package_files)} files. Excluded: {result.excluded_count} paths.")
        print("Upload these three files separately on HackerRank. Transcript structure checked; authenticity/completeness and prediction correctness are not verified.")
        return 0


def print_results(result):
    print(f"Orchestrate CLI {CLI_VERSION}; contract {CONTRACT_ID}")
    print(f"Submission checks: {result.totals['error']} errors, {result.totals['warning']} warnings.")
    for finding in result.findings:
        row = f", logical CSV record {finding.row} (not physical line)" if finding.row else ""
        # repr escapes terminal controls in participant-controlled paths.
        print(f"\n[{finding.code}] {finding.severity.upper()} {ascii(finding.path)}{row}\n{finding.message}\n{finding.hint}")
    for code, count in result.occurrences.items():
        if count > 5:
            print(f"[{code}] {count} total findings; first 5 shown.")
    if result.excluded_count:
        print(f"Excluded {result.excluded_count} paths (files or pruned directories); examples: " + ", ".join(ascii(p) for p in result.excluded))
    if not result.totals["error"]:
        print("Local format checks passed; transcript structure checked. This does not evaluate predictions or prove conversation completeness.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {CLI_VERSION} ({CONTRACT_ID})")
    parser.add_argument("command", choices=("check", "prepare"))
    args = parser.parse_args(argv)
    root = resolve_repo_root()
    # Allow realistic JSON cells larger than csv's small platform default.
    csv.field_size_limit(64 * 1024 * 1024)
    try:
        if args.command == "prepare":
            return prepare(root)
        result = run_checks(root)
        print_results(result)
        return 1 if result.totals["error"] else 0
    except (OperationalError, OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        print(f"Orchestrate CLI {CLI_VERSION}; contract {CONTRACT_ID}\nPreparation/check could not finish: {exc}\nNo new ready bundle is claimed; inspect recovery state if present.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
