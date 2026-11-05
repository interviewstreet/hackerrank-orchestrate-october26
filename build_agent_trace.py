#!/usr/bin/env python3
"""Stage Claude Code session traces for this repo and zip them as agent-trace.zip.

Run it on the computer where the Claude Code sessions ran, AFTER quitting those sessions (see agent_trace_instructions.md):

    python3 build_agent_trace.py                 # copy, scan for secrets, zip
    python3 build_agent_trace.py --list          # only show which session files would be included
    python3 build_agent_trace.py --rescan        # after redacting staged files: re-scan and zip without copying again
    python3 build_agent_trace.py --projects-dir PATH --match erasight

What it does: copies the .jsonl session files (and any sub-agent folders) from ~/.claude/projects/<folders whose name
contains "erasight"> into agent-trace/claude-code/, scans the copies for secret-looking strings, and zips only if the scan is clean.
It never copies settings, credentials or .env files. You still have to: add your /export transcripts and any other harness's traces
(agent-trace/<harness>/), and read through the staged files once before submitting.
Standard library only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

SECRET_PATTERNS = {
    "Groq key": re.compile(r"gsk_[A-Za-z0-9]{16,}"),
    "Resend key": re.compile(r"\bre_[A-Za-z0-9_]{20,}"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "Webhook secret": re.compile(r"whsec_[A-Za-z0-9+/=]{20,}"),
    "AWS key id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Key assignment": re.compile(r"(?:API_KEY|SECRET|TOKEN|PASSWORD)\s*[=:]\s*[\"']?[A-Za-z0-9_\-+/=]{16,}"),
}
# The official Svix webhook test vector is public and is used by this repo's tests.
ALLOWED = ("whsec_plJ3nmyCDGBKInavdOK15jsl",)


def find_session_dirs(projects_dir: Path, match: str):
    if not projects_dir.is_dir():
        return []
    return sorted(p for p in projects_dir.iterdir() if p.is_dir() and match.lower() in p.name.lower())


def stage(dirs, dest: Path) -> int:
    n = 0
    for d in dirs:
        for f in sorted(d.rglob("*")):
            if f.is_file():
                target = dest / d.name / f.relative_to(d)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
                n += 1
    return n


def scan(root: Path):
    hits = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for label, rx in SECRET_PATTERNS.items():
            for m in rx.finditer(text):
                if not any(a in m.group(0) for a in ALLOWED):
                    hits.append((f, label, text.count("\n", 0, m.start()) + 1))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects-dir", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--match", default="erasight", help="substring of the project folder name (case-insensitive)")
    ap.add_argument("--out", default="agent-trace", help="staging folder (created next to this script's working directory)")
    ap.add_argument("--list", action="store_true", help="list matching session files and exit")
    ap.add_argument("--rescan", action="store_true", help="skip copying; re-scan and zip the existing staging folder (after redacting)")
    args = ap.parse_args()

    dirs = find_session_dirs(Path(args.projects_dir), args.match)
    if not dirs:
        print(f"No project folder containing '{args.match}' under {args.projects_dir}.")
        print("Check the folder name with: ls ~/.claude/projects  (or dir %USERPROFILE%\\.claude\\projects)")
        return 1
    if args.list:
        for d in dirs:
            files = [f for f in d.rglob("*") if f.is_file()]
            print(f"{d}  ({len(files)} files)")
            for f in sorted(files):
                print("   ", f.relative_to(d))
        return 0

    out = Path(args.out)
    dest = out / "claude-code"
    if args.rescan:
        if not out.is_dir():
            print(f"{out} does not exist; run without --rescan first.")
            return 1
    else:
        if dest.exists():
            print(f"{dest} already exists; move or delete it first so old files are not mixed in "
                  "(or use --rescan to re-check what is already staged).")
            return 1
        count = stage(dirs, dest)
        print(f"Copied {count} file(s) into {dest}")

    hits = scan(out)
    if hits:
        print("\nPossible secrets found. Redact them in the staged copies (or delete those files), then run again with --rescan:")
        for f, label, line in hits[:40]:
            print(f"  {f}:{line}  [{label}]")
        print("\nNo zip was written.")
        return 2

    zpath = Path(str(out) + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, f.as_posix())
    print(f"Secret scan clean. Wrote {zpath}.")
    print("Before submitting: add your /export transcripts (and any other harness) to the agent-trace folder, "
          "re-zip if you added files, and open the zip once to check it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
