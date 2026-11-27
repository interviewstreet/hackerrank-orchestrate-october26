#!/usr/bin/env python3
"""orchestrate - HackerRank Orchestrate helper CLI.

One dependency-free file (Python 3.8+, macOS / Linux / Windows). It never
modifies agent settings, installs hooks, or talks to the network.

    orchestrate submit     collect agent traces, validate output.csv and log.txt, build agent-trace.zip
    orchestrate trace      only collect + redact + zip the agent traces
    orchestrate check      only validate output.csv (and log.txt)
    orchestrate doctor     show what would be collected and why
    orchestrate log        append a validated entry to log.txt (used by the coding agent)

Trace collection is read-only on every agent's own files: sessions are matched to
this repository by the working directory they recorded, copied into the zip,
and secrets are masked in the copies only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fnmatch
import getpass
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

if sys.version_info < (3, 8):
    sys.stderr.write("orchestrate needs Python 3.8 or newer.\n")
    sys.exit(127)

VERSION = "1.0.0"
ZIP_NAME = "agent-trace.zip"
ARC_ROOT = "agent-trace"
MANUAL_DIR = "agent-trace"
SUBMIT_URL = "https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists"
LIVE_WINDOW_SECONDS = 180
MAX_FILE_BYTES = 200 * 1024 * 1024
BIN_SCAN_BYTES = 50 * 1024 * 1024
WARN_TOTAL_BYTES = 300 * 1024 * 1024
EXPECTED_ROWS = 518

# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------


def eprint(*a):
    print(*a, file=sys.stderr)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%d %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f GB" % n


def norm(p) -> str:
    s = str(p).replace("\\", "/")
    while len(s) > 1 and s.endswith("/"):
        s = s[:-1]
    if re.match(r"^[A-Za-z]:", s) or os.name == "nt":
        s = s.lower()
    return s


def under(candidate: str, roots: Iterable[str]) -> bool:
    n = norm(candidate)
    for r in roots:
        if n == r or n.startswith(r + "/"):
            return True
    return False


def run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 30) -> Tuple[int, bytes]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, b""


def git_out(repo: Path, *args: str) -> str:
    rc, out = run(["git"] + list(args), cwd=repo)
    return out.decode("utf-8", "replace").strip() if rc == 0 else ""


def repo_roots(repo: Path) -> List[str]:
    """Every path form under which sessions may have recorded this repo."""
    cands = {str(repo), str(repo.resolve())}
    top = git_out(repo, "rev-parse", "--show-toplevel")
    if top:
        cands.add(top)
    wt = git_out(repo, "worktree", "list", "--porcelain")
    for line in wt.splitlines():
        if line.startswith("worktree "):
            cands.add(line[len("worktree "):].strip())
    out = set()
    for c in cands:
        out.add(norm(c))
        try:
            out.add(norm(Path(c).resolve()))
        except OSError:
            pass
    return sorted(out)


# ---------------------------------------------------------------------------
# redaction
# ---------------------------------------------------------------------------

_R = re.compile
SECRET_RULES: List[Tuple[str, "re.Pattern", str]] = [
    ("private-key", _R(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----.*?-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----", re.S), "[REDACTED]"),
    ("anthropic-key", _R(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "[REDACTED]"),
    ("openai-key", _R(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{32,}"), "[REDACTED]"),
    ("github-token", _R(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"), "[REDACTED]"),
    ("aws-access-key", _R(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED]"),
    ("google-api-key", _R(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "[REDACTED]"),
    ("slack-token", _R(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "[REDACTED]"),
    ("hf-token", _R(r"\bhf_[A-Za-z0-9]{30,}\b"), "[REDACTED]"),
    ("jwt", _R(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), "[REDACTED]"),
    ("bearer-token", _R(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/\-]{20,}=*"), r"\1[REDACTED]"),
    ("url-credentials", _R(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^\s/:@\"'\\]+:[^\s/@\"'\\]+@"), r"\1[REDACTED]@"),
    ("assigned-secret", _R(
        r"(?i)\b([A-Z0-9_\-]*(?:API[_\-]?KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE[_\-]?KEY|ACCESS[_\-]?KEY|CLIENT[_\-]?SECRET)[A-Z0-9_\-]*)"
        r"(\\?[\"']?\s*[:=]\s*\\?[\"']?)"
        r"(?!os\.|process\.|\$|env|getenv|none|null|true|false|<|\[REDACTED|\*+)"
        r"([^\s\"'\\,;}{)\]]{8,})"), r"\1\2[REDACTED]"),
]

TEXT_EXT = {".jsonl", ".json", ".md", ".txt", ".log", ".yaml", ".yml", ".toml", ".csv", ".sql",
            ".xml", ".html", ".htm", ".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".ini", ".cfg", ""}


def username_rule(user: str):
    if not user or len(user) < 2 or user.lower() in {"root", "user", "admin", "runner"}:
        return None
    return _R(r"((?:/Users/|/home/)|(?:[A-Za-z]:(?:\\{1,2}|/)Users(?:\\{1,2}|/)))" + re.escape(user) + r"(?![A-Za-z0-9_.\-])")


def arc_user_rule(user: str):
    """Agents encode the project path (with the username) into folder names; mask it in zip entry names too."""
    if not user or len(user) < 2 or user.lower() in {"root", "user", "admin", "runner"}:
        return None
    return _R(r"((?:Users|home)[-_/\\])" + re.escape(user) + r"(?![A-Za-z0-9])", re.I)


def redact_text(text: str, scrub_user: Optional["re.Pattern"] = None) -> Tuple[str, Dict[str, int]]:
    counts: Dict[str, int] = {}
    for name, pat, repl in SECRET_RULES:
        text, n = pat.subn(repl, text)
        if n:
            counts[name] = counts.get(name, 0) + n
    if scrub_user is not None:
        text, n = scrub_user.subn(r"\1<user>", text)
        if n:
            counts["username-in-path"] = n
    return text, counts


def scan_text(text: str) -> Dict[str, int]:
    return {name: len(pat.findall(text)) for name, pat, _ in SECRET_RULES if pat.search(text)}


SECRET_NAME_PATTERNS = [
    ".env*", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.kdbx", "id_rsa*", "id_ed25519*",
    "auth*.json", "*credential*", "mcp*.json", "oauth*", "settings*.json", "config.json", "config.toml",
    "hosts.yml", ".netrc", "*.token", "installation_id", "keybindings.json",
]


def is_secret_name(name: str) -> bool:
    n = name.lower()
    return any(fnmatch.fnmatch(n, p) for p in SECRET_NAME_PATTERNS)


# ---------------------------------------------------------------------------
# session model
# ---------------------------------------------------------------------------


class Session:
    def __init__(self, harness: str, sid: str, reason: str, best_effort: bool = False):
        self.harness = harness
        self.sid = sid
        self.reason = reason
        self.best_effort = best_effort
        self.files: List[Tuple[Path, str]] = []   # (source path, archive name below agent-trace/)
        self.blobs: List[Tuple[str, bytes]] = []  # (archive name, generated bytes)
        self.skipped: List[str] = []
        self.warnings: List[str] = []

    def add_tree(self, root: Path, arcbase: str):
        self.files.extend(walk_files(root, arcbase, self.skipped))

    def add_file(self, path: Path, arc: str):
        if path.is_symlink() or not path.is_file():
            return
        if is_secret_name(path.name):
            self.skipped.append(path.name)
            return
        self.files.append((path, arc))

    def stats(self) -> Tuple[int, float, float]:
        size, lo, hi = 0, None, None
        for p, _ in self.files:
            try:
                st = p.stat()
            except OSError:
                continue
            size += st.st_size
            lo = st.st_mtime if lo is None else min(lo, st.st_mtime)
            hi = st.st_mtime if hi is None else max(hi, st.st_mtime)
        for _, b in self.blobs:
            size += len(b)
        now = time.time()
        return size, (lo or now), (hi or now)


def walk_files(root: Path, arcbase: str, skipped: List[str]) -> List[Tuple[Path, str]]:
    out: List[Tuple[Path, str]] = []
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return out
    for dp, dns, fns in os.walk(str(root), followlinks=False):
        dns[:] = sorted(d for d in dns if not Path(dp, d).is_symlink())
        for fn in sorted(fns):
            p = Path(dp, fn)
            if p.is_symlink() or not p.is_file():
                continue
            if is_secret_name(fn):
                skipped.append(fn)
                continue
            rel = p.relative_to(root).as_posix()
            out.append((p, (arcbase.rstrip("/") + "/" + rel) if arcbase else rel))
    return out


def deep_values(obj, key: str, depth: int = 0) -> List[str]:
    found: List[str] = []
    if depth > 6:
        return found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                found.append(v)
            elif isinstance(v, (dict, list)):
                found.extend(deep_values(v, key, depth + 1))
    elif isinstance(obj, list):
        for v in obj[:50]:
            if isinstance(v, (dict, list)):
                found.extend(deep_values(v, key, depth + 1))
    return found


def head_cwds(path: Path, max_lines: int = 300, max_bytes: int = 2 << 20) -> Set[str]:
    cwds: Set[str] = set()
    try:
        with open(str(path), "rb") as f:
            read = 0
            for i, line in enumerate(f):
                read += len(line)
                if b'"cwd"' in line and len(line) < (4 << 20):
                    try:
                        cwds.update(deep_values(json.loads(line), "cwd"))
                    except ValueError:
                        pass
                if i >= max_lines or read >= max_bytes:
                    break
    except OSError:
        pass
    return cwds


def file_mentions(path: Path, needles: List[bytes], limit: int = 64 << 20) -> bool:
    keep = max(len(n) for n in needles) if needles else 0
    tail = b""
    read = 0
    try:
        with open(str(path), "rb") as f:
            while read < limit:
                chunk = f.read(4 << 20)
                if not chunk:
                    break
                read += len(chunk)
                buf = tail + chunk
                if any(n in buf for n in needles):
                    return True
                tail = buf[-keep:] if keep else b""
    except OSError:
        pass
    return False


class Ctx:
    def __init__(self, repo: Path, home: Optional[Path] = None, env: Optional[Dict[str, str]] = None,
                 since: Optional[float] = None):
        self.repo = Path(repo).resolve()
        self.home = Path(home) if home else Path.home()
        self.env = dict(os.environ) if env is None else dict(env)
        self.roots = repo_roots(self.repo)
        self.since = since

    def envdir(self, name: str) -> Optional[Path]:
        v = self.env.get(name)
        return Path(v).expanduser() if v else None

    def xdg_data(self) -> Path:
        v = self.env.get("XDG_DATA_HOME")
        return Path(v) if v else self.home / ".local" / "share"

    def needles(self) -> List[bytes]:
        n: Set[bytes] = set()
        for r in self.roots:
            n.add(r.encode("utf-8"))
            n.add(r.replace("/", "\\\\").encode("utf-8"))  # JSON-escaped windows form
            n.add(r.replace("/", "\\").encode("utf-8"))
        return sorted(n)


# ---------------------------------------------------------------------------
# collectors: each returns (sessions, diagnostics)
# ---------------------------------------------------------------------------

Collected = Tuple[List[Session], List[str]]


def _exists(p: Path) -> str:
    return "found" if p.exists() else "missing"


def collect_claude(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    dirs: List[Path] = []
    e = ctx.envdir("CLAUDE_PROJECTS_DIR")
    if e:
        dirs.append(e)
    cfg = ctx.envdir("CLAUDE_CONFIG_DIR")
    dirs.append((cfg or ctx.home / ".claude") / "projects")
    xdg = ctx.envdir("XDG_CONFIG_HOME")
    dirs.append((xdg or ctx.home / ".config") / "claude" / "projects")
    seen: Set[str] = set()
    for pdir in dirs:
        if str(pdir) in seen:
            continue
        seen.add(str(pdir))
        diag.append("%s (%s)" % (pdir, _exists(pdir)))
        if not pdir.is_dir():
            continue
        encoded = {re.sub(r"[^A-Za-z0-9]", "-", r) for r in ctx.roots}
        for proj in sorted(pdir.iterdir()):
            if not proj.is_dir() or proj.is_symlink():
                continue
            for jl in sorted(proj.glob("*.jsonl")):
                cwds = head_cwds(jl)
                if cwds:
                    hit = any(under(c, ctx.roots) for c in cwds)
                    why = "recorded cwd inside this repo"
                else:
                    hit = any(proj.name.lower().startswith(x.lower()) for x in encoded)
                    why = "project folder name matches this repo"
                if not hit:
                    continue
                s = Session("claude-code", jl.stem, why)
                s.add_file(jl, "claude-code/%s/%s" % (proj.name, jl.name))
                comp = proj / jl.stem
                if comp.is_dir():
                    s.add_tree(comp, "claude-code/%s/%s" % (proj.name, jl.stem))
                sessions.append(s)
    return sessions, diag


def collect_codex(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    roots: List[Path] = []
    e = ctx.envdir("CODEX_SESSIONS_DIR")
    if e:
        roots.append(e)
    home = ctx.envdir("CODEX_HOME") or ctx.home / ".codex"
    roots.extend([home / "sessions", home / "archived_sessions"])
    seen: Set[str] = set()
    for root in roots:
        if str(root) in seen:
            continue
        seen.add(str(root))
        diag.append("%s (%s)" % (root, _exists(root)))
        if not root.is_dir():
            continue
        for jl in sorted(root.rglob("rollout-*.jsonl")):
            if jl.is_symlink():
                continue
            if any(under(c, ctx.roots) for c in head_cwds(jl)):
                s = Session("codex", jl.stem.replace("rollout-", ""), "recorded cwd inside this repo")
                s.add_file(jl, "codex/%s/%s" % (root.name, jl.relative_to(root).as_posix()))
                sessions.append(s)
    return sessions, diag


def collect_antigravity(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    gem = ctx.envdir("GEMINI_DIR") or ctx.home / ".gemini"
    needles = ctx.needles()
    for variant in ("antigravity", "antigravity-cli", "antigravity-ide"):
        brain = gem / variant / "brain"
        diag.append("%s (%s)" % (brain, _exists(brain)))
        if not brain.is_dir():
            continue
        for conv in sorted(brain.iterdir()):
            if not conv.is_dir() or conv.is_symlink():
                continue
            logs = conv / ".system_generated" / "logs"
            cand = sorted(logs.glob("*.jsonl")) if logs.is_dir() else []
            if not cand:
                continue
            if any(file_mentions(c, needles) for c in cand):
                s = Session("antigravity", conv.name, "transcript mentions this repo's path")
                s.add_tree(conv, "antigravity/%s/brain/%s" % (variant, conv.name))
                sessions.append(s)
    return sessions, diag


def _opencode_db_path(ctx: Ctx) -> Optional[Path]:
    v = ctx.env.get("OPENCODE_DB")
    if v:
        return Path(v)
    if shutil.which("opencode"):
        rc, out = run(["opencode", "db", "path"], timeout=15)
        txt = out.decode("utf-8", "replace").strip()
        if rc == 0 and txt:
            return Path(txt.splitlines()[-1])
    return ctx.xdg_data() / "opencode" / "opencode.db"


def _sqlite_rows(con: sqlite3.Connection, table: str, where: str = "", args: tuple = ()):
    cur = con.execute("SELECT * FROM %s %s" % (table, where), args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def collect_opencode(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    done_ids: Set[str] = set()
    # 1) official CLI export (preferred, matches the organizers' instructions)
    if shutil.which("opencode"):
        rc, out = run(["opencode", "session", "list", "--format", "json"], timeout=30)
        listed = []
        if rc == 0:
            try:
                data = json.loads(out.decode("utf-8", "replace"))
                listed = data if isinstance(data, list) else data.get("sessions", [])
            except ValueError:
                diag.append("opencode session list returned non-JSON")
        diag.append("opencode CLI: %d sessions listed" % len(listed))
        for item in listed:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id", ""))
            d = item.get("directory") or item.get("cwd") or item.get("path") or ""
            if not sid or not d or not under(d, ctx.roots):
                continue
            rc2, blob = run(["opencode", "session", "export", sid], timeout=120)
            if rc2 == 0 and blob.strip():
                s = Session("opencode", sid, "session directory inside this repo (opencode session export)")
                s.blobs.append(("opencode/%s.json" % sid, blob))
                sessions.append(s)
                done_ids.add(sid)
    else:
        diag.append("opencode CLI not on PATH")
    # 2) read the SQLite database directly (best effort, read-only)
    db = _opencode_db_path(ctx)
    if db is not None:
        diag.append("%s (%s)" % (db, _exists(db)))
    if db is not None and db.is_file():
        try:
            con = sqlite3.connect("file:%s?mode=ro" % db.as_posix(), uri=True, timeout=5)
            try:
                for row in _sqlite_rows(con, "session"):
                    sid = str(row.get("id", ""))
                    d = row.get("directory") or ""
                    if not sid or sid in done_ids or not d or not under(d, ctx.roots):
                        continue
                    msgs = _sqlite_rows(con, "message", "WHERE session_id = ?", (sid,))
                    parts = _sqlite_rows(con, "part", "WHERE session_id = ?", (sid,))
                    by_msg: Dict[str, list] = {}
                    for p in parts:
                        by_msg.setdefault(str(p.get("message_id")), []).append(p)
                    for m in msgs:
                        m["parts"] = by_msg.get(str(m.get("id")), [])
                    blob = json.dumps({"session": row, "messages": msgs}, ensure_ascii=False,
                                      default=lambda o: "<%d bytes>" % len(o) if isinstance(o, bytes) else str(o))
                    s = Session("opencode", sid, "session directory inside this repo (read from opencode.db)", True)
                    s.blobs.append(("opencode/%s.json" % sid, blob.encode("utf-8")))
                    sessions.append(s)
                    done_ids.add(sid)
            finally:
                con.close()
        except sqlite3.Error as exc:
            diag.append("could not read opencode.db: %s" % exc)
    # 3) legacy JSON storage layout
    legacy = ctx.xdg_data() / "opencode" / "storage"
    sess_root = legacy / "session"
    if sess_root.is_dir():
        diag.append("%s (found)" % sess_root)
        for sj in sorted(sess_root.rglob("ses_*.json")):
            try:
                meta = json.loads(sj.read_text("utf-8"))
            except (OSError, ValueError):
                continue
            sid = str(meta.get("id", sj.stem))
            if sid in done_ids or not under(str(meta.get("directory", "")), ctx.roots):
                continue
            s = Session("opencode", sid, "legacy storage; directory inside this repo", True)
            s.add_file(sj, "opencode/storage/session/%s" % sj.name)
            mdir = legacy / "message" / sid
            if mdir.is_dir():
                s.add_tree(mdir, "opencode/storage/message/%s" % sid)
                for mf in sorted(mdir.glob("msg_*.json")):
                    pdir = legacy / "part" / mf.stem
                    if pdir.is_dir():
                        s.add_tree(pdir, "opencode/storage/part/%s" % mf.stem)
            sessions.append(s)
    return sessions, diag


def collect_gemini(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    gem = ctx.envdir("GEMINI_DIR") or ctx.home / ".gemini"
    tmp = gem / "tmp"
    diag.append("%s (%s)" % (tmp, _exists(tmp)))
    if not tmp.is_dir():
        return sessions, diag
    hashes = {hashlib.sha256(r.encode("utf-8")).hexdigest() for r in ctx.roots}
    for d in sorted(tmp.iterdir()):
        if not d.is_dir() or d.is_symlink():
            continue
        why = None
        if d.name in hashes:
            why = "folder is the hash of this repo's path"
        else:
            pr = d / ".project_root"
            try:
                if pr.is_file() and under(pr.read_text("utf-8").strip(), ctx.roots):
                    why = ".project_root points inside this repo"
            except OSError:
                pass
        if why:
            s = Session("gemini-cli", d.name, why)
            s.add_tree(d, "gemini-cli/%s" % d.name)
            if s.files:
                sessions.append(s)
    return sessions, diag


def collect_cursor(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    base = ctx.home / ".cursor" / "projects"
    diag.append("%s (%s)" % (base, _exists(base)))
    if not base.is_dir():
        return sessions, diag
    encoded = {re.sub(r"[^A-Za-z0-9]", "-", r).strip("-").lower() for r in ctx.roots}
    for d in sorted(base.iterdir()):
        t = d / "agent-transcripts"
        if d.name.strip("-").lower() in encoded and t.is_dir():
            s = Session("cursor", d.name, "project folder name matches this repo", True)
            s.add_tree(t, "cursor/%s/agent-transcripts" % d.name)
            if s.files:
                sessions.append(s)
    return sessions, diag


def collect_copilot(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    base = (ctx.envdir("COPILOT_DIR") or ctx.home / ".copilot") / "session-state"
    diag.append("%s (%s)" % (base, _exists(base)))
    if not base.is_dir():
        return sessions, diag
    needles = ctx.needles()
    for d in sorted(base.iterdir()):
        ws = d / "workspace.yaml"
        if d.is_dir() and not d.is_symlink() and ws.is_file() and file_mentions(ws, needles, 1 << 20):
            s = Session("copilot-cli", d.name, "workspace.yaml points inside this repo", True)
            s.add_tree(d, "copilot-cli/%s" % d.name)
            sessions.append(s)
    return sessions, diag


def collect_aider(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    s = Session("aider", "history", "history files in the repo root")
    for name in (".aider.chat.history.md", ".aider.input.history", ".aider.llm.history"):
        s.add_file(ctx.repo / name, "aider/%s" % name)
    diag.append("%s/.aider.* (%s)" % (ctx.repo, "found" if s.files else "missing"))
    if s.files:
        sessions.append(s)
    return sessions, diag


def collect_manual(ctx: Ctx) -> Collected:
    sessions: List[Session] = []
    diag: List[str] = []
    d = ctx.repo / MANUAL_DIR
    diag.append("%s/ (%s)" % (d, _exists(d)))
    if d.is_dir():
        s = Session("manual", "agent-trace-folder", "files you placed in ./%s/" % MANUAL_DIR)
        s.add_tree(d, "")
        if s.files:
            sessions.append(s)
    return sessions, diag


COLLECTORS = [
    ("claude-code", collect_claude),
    ("codex", collect_codex),
    ("antigravity", collect_antigravity),
    ("opencode", collect_opencode),
    ("gemini-cli", collect_gemini),
    ("cursor", collect_cursor),
    ("copilot-cli", collect_copilot),
    ("aider", collect_aider),
    ("manual", collect_manual),
]


def collect_all(ctx: Ctx, only: Optional[List[str]] = None) -> Tuple[List[Session], Dict[str, List[str]]]:
    sessions: List[Session] = []
    diags: Dict[str, List[str]] = {}
    for name, fn in COLLECTORS:
        if only and name not in only:
            continue
        try:
            found, diag = fn(ctx)
        except Exception as exc:  # one broken harness must never block the others
            found, diag = [], ["error while scanning: %s" % exc]
        if ctx.since is not None:
            found = [s for s in found if s.harness == "manual" or s.stats()[2] >= ctx.since]
        sessions.extend(found)
        diags[name] = diag
    return sessions, diags


# ---------------------------------------------------------------------------
# trace packaging
# ---------------------------------------------------------------------------


def process_bytes(arc: str, data: bytes, scrub: Optional["re.Pattern"]) -> Tuple[bytes, Dict[str, int], List[str]]:
    ext = os.path.splitext(arc)[1].lower()
    warns: List[str] = []
    if ext in TEXT_EXT:
        text = data.decode("utf-8", "surrogateescape")
        text, counts = redact_text(text, scrub)
        out = text.encode("utf-8", "surrogateescape")
        if ext == ".jsonl":
            last = out.rstrip(b"\n").rsplit(b"\n", 1)[-1]
            try:
                json.loads(last)
            except ValueError:
                warns.append("last line is not valid JSON (file may still be written to)")
        return out, counts, warns
    if len(data) <= BIN_SCAN_BYTES:
        hits = scan_text(data.decode("latin-1"))
        if hits:
            warns.append("binary file contains possible secrets (%s) that cannot be masked; review it" %
                         ", ".join(sorted(hits)))
    return data, {}, warns


def zip_date(mtime: float):
    t = time.localtime(max(mtime, 315532800))
    return t[:6]


def print_preview(sessions: List[Session], verbose: bool):
    by: Dict[str, List[Session]] = {}
    for s in sessions:
        by.setdefault(s.harness, []).append(s)
    now = time.time()
    for h, group in by.items():
        total = sum(s.stats()[0] for s in group)
        print("  %-13s %d session(s), %s%s" % (h, len(group), human(total),
                                                  "  [best-effort adapter]" if any(s.best_effort for s in group) else ""))
        for s in group[: (len(group) if verbose else 8)]:
            size, _, hi = s.stats()
            live = "  LIVE (still being written)" if now - hi < LIVE_WINDOW_SECONDS else ""
            print("      %-38s %s  %3d file(s) %9s%s" % (
                s.sid[:38], time.strftime("%Y-%m-%d %H:%M", time.localtime(hi)),
                len(s.files) + len(s.blobs), human(size), live))
        if len(group) > 8 and not verbose:
            print("      ... and %d more (use --verbose)" % (len(group) - 8))


def build_zip(ctx: Ctx, sessions: List[Session], out_path: Path, keep_paths: bool) -> Dict:
    scrub = None if keep_paths else username_rule(_username(ctx))
    entries: Dict[str, Tuple[Optional[Path], Optional[bytes], Session]] = {}
    dup: List[str] = []
    arc_scrub = None if keep_paths else arc_user_rule(_username(ctx))
    for s in sessions:
        for p, arc in s.files:
            if arc_scrub is not None:
                arc = arc_scrub.sub(r"\1user", arc)
            key = "%s/%s" % (ARC_ROOT, arc) if arc else ARC_ROOT
            if key in entries:
                dup.append(key)
                continue
            entries[key] = (p, None, s)
        for arc, b in s.blobs:
            key = "%s/%s" % (ARC_ROOT, arc)
            if key in entries:
                dup.append(key)
                continue
            entries[key] = (None, b, s)
    redactions: Dict[str, int] = {}
    file_warnings: List[Dict] = []
    skipped_big: List[str] = []
    manifest_files: List[Dict] = []
    tmp = out_path.with_name(".%s.tmp" % out_path.name)
    total_in = 0
    with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED) as z:
        for key in sorted(entries):
            p, blob, s = entries[key]
            try:
                if p is not None:
                    size = p.stat().st_size
                    if size > MAX_FILE_BYTES:
                        skipped_big.append(key)
                        continue
                    data = p.read_bytes()
                    mtime = p.stat().st_mtime
                else:
                    data, mtime = blob, time.time()
            except OSError as exc:
                file_warnings.append({"file": key, "warning": "could not read (%s); skipped" % exc})
                continue
            total_in += len(data)
            data, counts, warns = process_bytes(key, data, scrub)
            for k, v in counts.items():
                redactions[k] = redactions.get(k, 0) + v
            for w in warns:
                file_warnings.append({"file": key, "warning": w})
            zi = zipfile.ZipInfo(key, date_time=zip_date(mtime))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
            manifest_files.append({"path": key, "bytes": len(data), "harness": s.harness})
        manifest = {
            "tool": "orchestrate %s" % VERSION,
            "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "repo": ctx.repo.name,
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "sessions": [{
                "harness": s.harness, "id": s.sid, "matched_because": s.reason,
                "best_effort_adapter": s.best_effort, "files": len(s.files) + len(s.blobs),
                "last_modified": dt.datetime.fromtimestamp(s.stats()[2]).astimezone().isoformat(timespec="seconds"),
                "possibly_incomplete_live_session": time.time() - s.stats()[2] < LIVE_WINDOW_SECONDS,
                "credential_files_not_copied": len(s.skipped),
            } for s in sessions],
            "redactions": redactions,
            "warnings": file_warnings,
            "skipped_too_large": skipped_big,
            "duplicate_paths_ignored": dup,
            "files": manifest_files,
        }
        z.writestr(zipfile.ZipInfo("%s/MANIFEST.json" % ARC_ROOT, date_time=zip_date(time.time())),
                   json.dumps(manifest, indent=2, ensure_ascii=False))
    replaced = None
    if out_path.exists():
        prev = out_path.with_name("agent-trace.prev.zip")
        os.replace(str(out_path), str(prev))
        replaced = prev.name
    os.replace(str(tmp), str(out_path))
    return {"files": len(manifest_files), "redactions": redactions, "warnings": file_warnings,
            "skipped_big": skipped_big, "dups": dup, "bytes_in": total_in, "replaced": replaced}


def _username(ctx: Ctx) -> str:
    try:
        return getpass.getuser()
    except Exception:
        return ctx.home.name


def parse_since(v: Optional[str]) -> Optional[float]:
    if not v:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(v, fmt))
        except ValueError:
            continue
    raise SystemExit("--since expects YYYY-MM-DD or YYYY-MM-DDTHH:MM")


def cmd_trace(args, ctx: Ctx) -> int:
    only = [x.strip() for x in args.only.split(",")] if args.only else None
    sessions, diags = collect_all(ctx, only)
    real = [s for s in sessions if s.files or s.blobs]
    print("Repository: %s" % ctx.repo)
    if not real:
        print("\nNo agent sessions matched this repository.\n")
        print("What to do:")
        print("  1. Run `orchestrate doctor` to see which folders were checked.")
        print("  2. If your tool is not auto-detected (or it was a hosted/cloud session), export or copy its")
        print("     transcript files into ./%s/<tool-name>/ and run this command again." % MANUAL_DIR)
        print("  3. If you ran the agent from a different folder than this repo, set the tool's session folder")
        print("     env var (see `orchestrate doctor`) or copy the files by hand as in step 2.")
        return 2
    print("\nSessions that will be included:")
    print_preview(real, args.verbose)
    best = sum(1 for s in real if s.best_effort)
    skipped = sum(len(s.skipped) for s in real)
    if skipped:
        print("\n  %d credential/config file(s) were left out on purpose (auth, settings, MCP, .env ...)." % skipped)
    if best:
        print("  Note: sessions marked [best-effort adapter] come from a format we could only partly verify.")
    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0
    out_path = ctx.repo / ZIP_NAME
    if sys.stdin.isatty() and not args.yes:
        ans = input("\nWrite %s with these sessions? Secrets are masked in the copy. [y/N] " % ZIP_NAME)
        if ans.strip().lower() not in ("y", "yes"):
            print("Aborted. Nothing written.")
            return 1
    res = build_zip(ctx, real, out_path, args.keep_paths)
    print("\nWrote %s  (%d files, %s)" % (out_path, res["files"], human(out_path.stat().st_size)))
    if res["replaced"]:
        print("  Previous zip kept as %s" % res["replaced"])
    if res["redactions"]:
        print("  Masked in the copy: " + ", ".join("%s x%d" % kv for kv in sorted(res["redactions"].items())))
    else:
        print("  No secret patterns found.")
    for w in res["warnings"][:15]:
        print("  ! %s: %s" % (w["file"], w["warning"]))
    if len(res["warnings"]) > 15:
        print("  ! ... %d more warnings in MANIFEST.json" % (len(res["warnings"]) - 15))
    for k in res["skipped_big"]:
        print("  ! skipped (over %s): %s" % (human(MAX_FILE_BYTES), k))
    if res["bytes_in"] > WARN_TOTAL_BYTES:
        print("  ! The traces are large (%s). Check the upload size limit." % human(res["bytes_in"]))
    now = time.time()
    if any(now - s.stats()[2] < LIVE_WINDOW_SECONDS for s in real):
        print("\n  A session is still being written (the one running this command). Its last turn is missing.")
        print("  After you finish and close your agent, run `orchestrate trace` once more.")
    print("\nReview the zip before uploading: traces can contain code, prompts and file paths.")
    return 0


def cmd_doctor(args, ctx: Ctx) -> int:
    print("orchestrate %s  python %s  %s" % (VERSION, sys.version.split()[0], sys.platform))
    print("repo   : %s" % ctx.repo)
    print("home   : %s" % ctx.home)
    print("roots  : %s" % ", ".join(ctx.roots))
    git = shutil.which("git")
    print("git    : %s" % (git or "not found (worktree detection disabled)"))
    hint = detect_harness_env(ctx.env)
    if hint:
        print("running inside: %s" % hint)
    print("env overrides honoured: CLAUDE_PROJECTS_DIR CLAUDE_CONFIG_DIR CODEX_HOME CODEX_SESSIONS_DIR "
          "GEMINI_DIR OPENCODE_DB XDG_DATA_HOME COPILOT_DIR")
    sessions, diags = collect_all(ctx)
    print()
    for name, _ in COLLECTORS:
        group = [s for s in sessions if s.harness == name]
        print("%-12s %d matching session(s)" % (name, len(group)))
        for line in diags.get(name, []):
            print("    checked: %s" % line)
        for s in group[:5]:
            print("    - %s  (%s)" % (s.sid[:40], s.reason))
    print("\nNot listed here? Copy its transcript files into ./%s/<tool-name>/ and run `orchestrate trace`." % MANUAL_DIR)
    return 0


def detect_harness_env(env: Dict[str, str]) -> Optional[str]:
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        return "Claude Code (CLAUDECODE is set)"
    if env.get("CODEX_SANDBOX") or env.get("CODEX_THREAD_ID") or env.get("CODEX_HOME"):
        return "Codex (CODEX_* is set)"
    if env.get("OPENCODE") or env.get("OPENCODE_SERVER_PASSWORD"):
        return "OpenCode"
    if env.get("GEMINI_CLI"):
        return "Gemini CLI"
    if env.get("CURSOR_TRACE_ID"):
        return "Cursor"
    return None


# ---------------------------------------------------------------------------
# output.csv validation
# ---------------------------------------------------------------------------

OPS = {
    "REPORT_REMAINING_RECORD": ("FINDING", "PRESENT"), "REPORT_EXPOSED_PII": ("FINDING", "PRESENT"),
    "REPORT_ACTIVE_DATA_FLOW": ("FINDING", "ACTIVE"), "REPORT_RESTORE_RISK": ("FINDING", "ACTIVE"),
    "DISABLE_DATA_FLOW": ("REMEDIATION", "DISABLED"), "BLOCK_RESTORE": ("REMEDIATION", "BLOCKED"),
    "DELETE_RECORD": ("REMEDIATION", "ABSENT"), "REDACT_RECORD": ("REMEDIATION", "REDACTED"),
    "ANONYMIZE_RECORD": ("REMEDIATION", "ANONYMIZED"),
    "VERIFY_RECORD_ABSENT": ("VERIFICATION", "ABSENT"), "VERIFY_RECORD_PRESENT": ("VERIFICATION", "PRESENT"),
    "VERIFY_RECORD_REDACTED": ("VERIFICATION", "REDACTED"), "VERIFY_RECORD_ANONYMIZED": ("VERIFICATION", "ANONYMIZED"),
    "VERIFY_DATA_FLOW_DISABLED": ("VERIFICATION", "DISABLED"), "VERIFY_RESTORE_BLOCKED": ("VERIFICATION", "BLOCKED"),
}
PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
STEP_KEYS = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}


def _read_csv(path: Path) -> Tuple[List[str], List[List[str]]]:
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2 ** 31 - 1)
    with open(str(path), newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return (rows[0] if rows else []), rows[1:]


def check_output(repo: Path) -> Tuple[List[str], List[str], Dict[str, int]]:
    errors: List[str] = []
    warns: List[str] = []
    stats: Dict[str, int] = {}
    out = repo / "output.csv"
    if not out.is_file():
        return ["output.csv not found at the repository root (%s)" % out], warns, stats
    expected_ids: Optional[List[str]] = None
    req = repo / "dataset" / "deletion_requests.csv"
    if req.is_file():
        h, rows = _read_csv(req)
        if "case_id" in h:
            expected_ids = [r[h.index("case_id")] for r in rows if r]
    else:
        warns.append("dataset/deletion_requests.csv not found; checking against the expected %d rows only" % EXPECTED_ROWS)
    header, rows = _read_csv(out)
    if header != ["case_id", "deletion_status", "steps_json"]:
        errors.append("header must be exactly case_id,deletion_status,steps_json (got %s)" % ",".join(header))
        return errors, warns, stats
    want = len(expected_ids) if expected_ids is not None else EXPECTED_ROWS
    if len(rows) != want:
        errors.append("expected %d data rows, found %d" % (want, len(rows)))
    ids = [r[0] if r else "" for r in rows]
    if len(set(ids)) != len(ids):
        dups = sorted({i for i in ids if ids.count(i) > 1})
        errors.append("duplicate case_id values: %s" % ", ".join(dups[:10]))
    if expected_ids is not None:
        missing = sorted(set(expected_ids) - set(ids))
        extra = sorted(set(ids) - set(expected_ids))
        if missing:
            errors.append("%d case_id(s) missing, e.g. %s" % (len(missing), ", ".join(missing[:5])))
        if extra:
            errors.append("%d unknown case_id(s), e.g. %s" % (len(extra), ", ".join(extra[:5])))
    if ids != sorted(ids):
        errors.append("rows are not sorted by case_id")
    for ln, r in enumerate(rows, start=2):
        if len(r) != 3:
            errors.append("line %d: expected 3 columns, found %d" % (ln, len(r)))
            continue
        cid, status, raw = r
        stats[status] = stats.get(status, 0) + 1
        if status not in STATUSES:
            errors.append("%s: deletion_status %r is not one of %s" % (cid, status, "/".join(sorted(STATUSES))))
            continue
        try:
            steps = json.loads(raw)
        except ValueError as exc:
            errors.append("%s: steps_json is not valid JSON (%s)" % (cid, exc))
            continue
        if not isinstance(steps, list):
            errors.append("%s: steps_json must be a JSON array" % cid)
            continue
        if status == "NOT_APPLICABLE":
            if steps:
                errors.append("%s: NOT_APPLICABLE requires steps_json=[]" % cid)
            continue
        if not steps:
            errors.append("%s: %s needs at least one step" % (cid, status))
            continue
        errors.extend(_check_steps(cid, status, steps, warns))
    return errors, warns, stats


def _check_steps(cid: str, status: str, steps: list, warns: List[str]) -> List[str]:
    errs: List[str] = []
    last_phase = -1
    for i, st in enumerate(steps, start=1):
        if not isinstance(st, dict):
            errs.append("%s: step %d is not an object" % (cid, i))
            continue
        if set(st) != STEP_KEYS:
            diff = sorted(set(st) ^ STEP_KEYS)
            errs.append("%s: step %d has wrong fields (%s)" % (cid, i, ", ".join(diff)))
            continue
        if isinstance(st["step_no"], bool) or st["step_no"] != i:
            errs.append("%s: step_no must be consecutive from 1 (step %d has %r)" % (cid, i, st["step_no"]))
        for k in STEP_KEYS - {"step_no"}:
            if not isinstance(st[k], str):
                errs.append("%s: step %d field %s must be a string" % (cid, i, k))
        op, phase, state = st.get("operation"), st.get("phase"), st.get("state")
        if op not in OPS:
            errs.append("%s: step %d unknown operation %r" % (cid, i, op))
        else:
            exp_phase, exp_state = OPS[op]
            if phase != exp_phase:
                errs.append("%s: step %d operation %s belongs to phase %s, not %s" % (cid, i, op, exp_phase, phase))
            if state != exp_state:
                errs.append("%s: step %d operation %s requires state %s, not %s" % (cid, i, op, exp_state, state))
        if phase not in PHASE_ORDER:
            errs.append("%s: step %d unknown phase %r" % (cid, i, phase))
        else:
            if PHASE_ORDER[phase] < last_phase:
                errs.append("%s: step %d phase %s is out of order (FINDING, REMEDIATION, VERIFICATION)" % (cid, i, phase))
            last_phase = max(last_phase, PHASE_ORDER[phase])
        ev = st.get("evidence_id")
        if phase == "FINDING" and not ev:
            warns.append("%s: FINDING step %d should cite an evidence_id" % (cid, i))
        if phase == "REMEDIATION" and ev:
            warns.append("%s: REMEDIATION step %d should have an empty evidence_id" % (cid, i))
        if status == "COMPLETE" and phase != "VERIFICATION":
            warns.append("%s: COMPLETE cases should contain only VERIFICATION steps" % cid)
        if status == "COMPLETE" and phase == "VERIFICATION" and not ev:
            warns.append("%s: COMPLETE verification step %d should cite an evidence_id" % (cid, i))
        if status == "INCOMPLETE" and phase == "VERIFICATION" and ev:
            warns.append("%s: future verification step %d should have an empty evidence_id" % (cid, i))
    return errs


def cmd_check(args, ctx: Ctx) -> int:
    errors, warns, stats = check_output(ctx.repo)
    print("output.csv checks:")
    if stats:
        print("  rows by status: " + ", ".join("%s=%d" % kv for kv in sorted(stats.items())))
    for e in errors[:25]:
        print("  ERROR  %s" % e)
    if len(errors) > 25:
        print("  ERROR  ... and %d more" % (len(errors) - 25))
    uniq = list(dict.fromkeys(warns))
    for w in uniq[:10]:
        print("  warn   %s" % w)
    if len(uniq) > 10:
        print("  warn   ... and %d more" % (len(uniq) - 10))
    lerrs = check_log(ctx.repo)
    print("log.txt checks:")
    for e in lerrs[:15]:
        print("  ERROR  %s" % e)
    if not errors and not lerrs:
        print("  OK: output.csv and log.txt are valid.")
    return 1 if (errors or lerrs) else 0


# ---------------------------------------------------------------------------
# log.txt
# ---------------------------------------------------------------------------

GENERIC_TOOL = {"ai", "llm", "agent", "assistant", "bot", "unknown", "n/a", "na", "none", "null", "tbd", "todo",
                "coding agent", "ai assistant", "ai agent", "harness", "tool", "undefined"}
GENERIC_MODEL = GENERIC_TOOL | {"claude", "gpt", "gemini", "opus", "sonnet", "haiku", "auto", "default", "model"}
MODEL_LIKE = re.compile(r"^(?:claude|gpt|gemini|llama|mistral|qwen|deepseek|grok)-[a-z0-9.\-]*\d|^o\d(?:-|$)", re.I)
PLACEHOLDER = re.compile(r"[<>{}]|placeholder|template|\bexample\b", re.I)


def validate_tool(v: str) -> Optional[str]:
    v = (v or "").strip()
    if not v or v.lower() in GENERIC_TOOL or PLACEHOLDER.search(v):
        return "tool must be the exact name of the coding harness running now (for example 'Claude Code'), not %r" % v
    if MODEL_LIKE.match(v):
        return "tool=%r looks like a model name; put the harness name (not the model) in tool" % v
    return None


def validate_model(v: str) -> Optional[str]:
    v = (v or "").strip()
    if not v or v.lower() in GENERIC_MODEL or PLACEHOLDER.search(v) or not re.search(r"\d", v):
        return ("model must be the exact runtime model id taken from the harness/session metadata "
                "(for example 'claude-sonnet-5-5'), never a family name or a guess; got %r" % v)
    return None


def detect_language(repo: Path) -> str:
    if (repo / "tsconfig.json").exists():
        return "ts"
    if (repo / "package.json").exists():
        return "js"
    if any((repo / f).exists() for f in ("pyproject.toml", "requirements.txt", "setup.py")) or (repo / "code" / "main.py").exists():
        return "py"
    return "custom:unknown"


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _ctx_fields(repo: Path, tool: str, model: str, parent: str) -> List[str]:
    branch = git_out(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    gd = git_out(repo, "rev-parse", "--git-dir")
    gc = git_out(repo, "rev-parse", "--git-common-dir")
    worktree = "main"
    if gd and gc:
        try:
            if (repo / gd).resolve() != (repo / gc).resolve():
                worktree = git_out(repo, "rev-parse", "--show-toplevel") or str(repo)
        except OSError:
            pass
    return ["tool=%s" % tool, "model=%s" % model, "branch=%s" % branch,
            "repo_root=%s" % repo, "worktree=%s" % worktree, "parent_agent=%s" % parent]


def verify_entry(block: str) -> Optional[str]:
    tails = [l for l in block.splitlines() if l.startswith("tool=")], [l for l in block.splitlines() if l.startswith("model=")]
    return None if all(tails) else "tool= or model= line is missing after write"


def cmd_log(args, ctx: Ctx) -> int:
    for err in (validate_tool(args.tool), validate_model(args.model)):
        if err:
            eprint("orchestrate log: " + err)
            hint = detect_harness_env(ctx.env)
            if hint:
                eprint("  hint: this process looks like %s" % hint)
            return 2
    parent = (args.parent_agent or "none").strip() or "none"
    log = ctx.repo / "log.txt"
    if args.kind == "start":
        lang = args.language or detect_language(ctx.repo)
        body = ["## [%s] SESSION START" % _now(), ""] + [
            "tool=%s" % args.tool, "model=%s" % args.model, "Repo Root: %s" % ctx.repo,
            "Branch: %s" % (git_out(ctx.repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"),
            "Worktree: %s" % _ctx_fields(ctx.repo, args.tool, args.model, parent)[4].split("=", 1)[1],
            "Parent Agent: %s" % parent, "Language: %s" % lang,
            "Time Remaining: %s" % (args.time_remaining or "not configured")]
    else:
        if not args.title or not args.summary:
            eprint("orchestrate log turn: --title and --summary are required")
            return 2
        if args.prompt_stdin:
            prompt = sys.stdin.buffer.read().decode("utf-8", "replace")
        elif args.prompt_file:
            prompt = Path(args.prompt_file).read_text("utf-8")
        else:
            prompt = args.prompt or ""
        if not prompt.strip():
            eprint("orchestrate log turn: the verbatim user prompt is required (--prompt, --prompt-file or --prompt-stdin)")
            return 2
        prompt, _ = redact_text(prompt.rstrip("\n"))
        summary, _ = redact_text(args.summary.strip())
        actions = [redact_text(a)[0] for a in (args.action or [])] or ["(none)"]
        body = ["## [%s] %s" % (_now(), " ".join(args.title.split())[:80]), "",
                "User Prompt (verbatim, secrets redacted):", prompt, "",
                "Agent Response Summary:", summary, "", "Actions:"] + ["* %s" % a for a in actions] + [
                "", "Context:"] + _ctx_fields(ctx.repo, args.tool, args.model, parent)
    text = "\n".join(body) + "\n"
    existing = log.read_bytes() if log.exists() else b""
    prefix = b"" if not existing else (b"\n" if existing.endswith(b"\n") else b"\n\n")
    with open(str(log), "ab") as f:
        f.write(prefix + text.encode("utf-8"))
    written = log.read_bytes()[len(existing):].decode("utf-8")
    problem = verify_entry(written)
    if problem:
        eprint("orchestrate log: " + problem)
        return 1
    print("log.txt: appended %s entry (tool=%s, model=%s)" % (args.kind, args.tool, args.model))
    return 0


def check_log(repo: Path) -> List[str]:
    log = repo / "log.txt"
    if not log.is_file():
        return ["log.txt not found at the repository root"]
    text = log.read_text("utf-8", "replace")
    blocks = re.split(r"(?m)^## \[", text)[1:]
    if not blocks:
        return ["log.txt has no entries"]
    errs: List[str] = []
    if "SESSION START" not in blocks[0].splitlines()[0]:
        errs.append("log.txt should begin with a SESSION START entry")
    for b in blocks:
        head = b.splitlines()[0][:60]
        tools = re.findall(r"(?m)^tool=(.*)$", b)
        models = re.findall(r"(?m)^model=(.*)$", b)
        if not tools or not models:
            errs.append("entry '[%s' is missing tool= or model=" % head)
            continue
        for err in (validate_tool(tools[-1]), validate_model(models[-1])):
            if err:
                errs.append("entry '[%s': %s" % (head, err))
    return errs[:50]


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------


def cmd_submit(args, ctx: Ctx) -> int:
    print("== 1/3  output.csv and log.txt ==")
    rc_check = cmd_check(args, ctx)
    print("\n== 2/3  agent traces ==")
    rc_trace = cmd_trace(args, ctx)
    print("\n== 3/3  checklist ==")
    print("  [%s] output.csv valid and log.txt entries valid" % ("x" if rc_check == 0 else " "))
    print("  [%s] %s built (review it before uploading)" % ("x" if rc_trace == 0 else " ", ZIP_NAME))
    print("  [ ] code.zip: your solution, prompts, README.md, evaluation/evaluation_report.md and")
    print("      evaluation/usage_report.md. No dataset/, venvs, caches, nested archives or secrets.")
    print("  [ ] log.txt is the chat_transcript you upload.")
    print("\nSubmit at: %s" % SUBMIT_URL)
    return 0 if (rc_check == 0 and rc_trace == 0) else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orchestrate", description=__doc__.split("\n\n")[0])
    p.add_argument("--version", action="version", version="orchestrate %s" % VERSION)
    p.add_argument("--repo", help="repository root (default: the folder containing this script)")
    sub = p.add_subparsers(dest="cmd")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=argparse.SUPPRESS, help="repository root (default: this script's folder)")

    def trace_opts(sp):
        sp.add_argument("--yes", "-y", action="store_true", help="do not ask for confirmation")
        sp.add_argument("--dry-run", action="store_true", help="show what would be included, write nothing")
        sp.add_argument("--only", help="comma list of harnesses, e.g. claude-code,codex")
        sp.add_argument("--since", help="only sessions modified since YYYY-MM-DD[THH:MM]")
        sp.add_argument("--keep-paths", action="store_true", help="do not replace your username in file paths")
        sp.add_argument("--verbose", "-v", action="store_true", help="list every session")

    sp = sub.add_parser("submit", parents=[common], help="validate output.csv + log.txt, build agent-trace.zip, print checklist")
    trace_opts(sp)
    sp = sub.add_parser("trace", parents=[common], help="collect, redact and zip agent traces")
    trace_opts(sp)
    sub.add_parser("check", parents=[common], help="validate output.csv and log.txt")
    sub.add_parser("doctor", parents=[common], help="show detected harnesses and where traces were looked for")
    sp = sub.add_parser("log", parents=[common], help="append a validated entry to log.txt")
    sp.add_argument("kind", choices=["start", "turn"])
    sp.add_argument("--tool", required=True, help="exact harness name, e.g. 'Claude Code'")
    sp.add_argument("--model", required=True, help="exact runtime model id")
    sp.add_argument("--parent-agent")
    sp.add_argument("--language", help="js|ts|py|custom:name (start only; auto-detected if omitted)")
    sp.add_argument("--time-remaining")
    sp.add_argument("--title", help="turn title, max 80 chars")
    sp.add_argument("--summary", help="2-5 sentence response summary")
    sp.add_argument("--action", action="append", help="repeatable: file edited / command run")
    sp.add_argument("--prompt", help="verbatim user prompt")
    sp.add_argument("--prompt-file", help="read the verbatim prompt from a file")
    sp.add_argument("--prompt-stdin", action="store_true", help="read the verbatim prompt from stdin")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parent
    ctx = Ctx(repo, since=parse_since(getattr(args, "since", None)))
    try:
        return {"submit": cmd_submit, "trace": cmd_trace, "check": cmd_check,
                "doctor": cmd_doctor, "log": cmd_log}[args.cmd](args, ctx)
    except KeyboardInterrupt:
        eprint("\nInterrupted. Nothing was changed.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
