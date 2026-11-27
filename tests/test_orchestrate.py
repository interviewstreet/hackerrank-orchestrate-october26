import csv
import getpass
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import orchestrate as o  # noqa: E402

USER = getpass.getuser()
SECRET = "sk-ant-api03-" + "A1b2C3d4E5" * 4
GH = "ghp_" + "a1B2c3D4e5" * 4


def jl(path, *objs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) for x in objs) + "\n", encoding="utf-8")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.repo = base / "work space" / "orch repo"
        self.repo.mkdir(parents=True)
        self.home = base / "home"
        self.home.mkdir()
        self.other = base / "elsewhere"
        self.other.mkdir()
        self.env = {"OPENCODE_DB": str(self.home / "opencode.db")}
        self.ctx = o.Ctx(self.repo, home=self.home, env=self.env)

    def tearDown(self):
        self.tmp.cleanup()

    def make_all(self):
        r, h = str(self.repo), self.home
        enc = re.sub(r"[^A-Za-z0-9]", "-", r)
        cl = h / ".claude" / "projects" / enc
        jl(cl / "s1.jsonl", {"type": "user", "cwd": r + "/code", "message": "key %s path /Users/%s/x" % (SECRET, USER)})
        (cl / "s1").mkdir()
        (cl / "s1" / "sub.jsonl").write_text('{"a":1}\n')
        jl(h / ".claude" / "projects" / "-other" / "s2.jsonl", {"cwd": str(self.other)})
        jl(h / ".codex" / "sessions" / "2026" / "11" / "27" / "rollout-abc.jsonl",
           {"type": "session_meta", "payload": {"cwd": r, "token": GH}})
        jl(h / ".codex" / "sessions" / "2026" / "11" / "27" / "rollout-zzz.jsonl",
           {"type": "session_meta", "payload": {"cwd": str(self.other)}})
        ag = h / ".gemini" / "antigravity" / "brain" / "conv1"
        jl(ag / ".system_generated" / "logs" / "transcript_full.jsonl", {"args": {"file": r + "/a.py"}})
        (ag / "mcp_config.json").write_text('{"secret": "x"}')
        (ag / "walkthrough.md").write_text("hi")
        ag2 = h / ".gemini" / "antigravity-cli" / "brain" / "conv2"
        jl(ag2 / ".system_generated" / "logs" / "transcript.jsonl", {"x": str(self.other)})
        g = h / ".gemini" / "tmp" / hashlib.sha256(r.encode()).hexdigest() / "chats"
        g.mkdir(parents=True)
        (g / "session-1.json").write_text('{"messages":[]}')
        cu = h / ".cursor" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", r).strip("-") / "agent-transcripts"
        cu.mkdir(parents=True)
        (cu / "t.txt").write_text("cursor transcript")
        (self.repo / ".aider.chat.history.md").write_text("aider chat")
        (self.repo / "agent-trace" / "windsurf").mkdir(parents=True)
        (self.repo / "agent-trace" / "windsurf" / "export.md").write_text("manual export")
        con = sqlite3.connect(self.env["OPENCODE_DB"])
        con.execute("create table session (id text, directory text, title text)")
        con.execute("create table message (id text, session_id text, data text)")
        con.execute("create table part (id text, message_id text, session_id text, data text)")
        con.execute("insert into session values ('ses_1', ?, 't')", (r,))
        con.execute("insert into session values ('ses_2', ?, 't')", (str(self.other),))
        con.execute("insert into message values ('m1','ses_1','{}')")
        con.execute("insert into part values ('p1','m1','ses_1','{\"text\":\"hello\"}')")
        con.commit()
        con.close()


class CollectTests(Fixture):
    def test_each_harness_matched_and_strangers_ignored(self):
        self.make_all()
        sessions, _ = o.collect_all(self.ctx)
        got = sorted((s.harness, s.sid) for s in sessions)
        names = {h for h, _ in got}
        self.assertEqual(names, {"claude-code", "codex", "antigravity", "opencode", "gemini-cli", "cursor", "aider", "manual"})
        self.assertIn(("claude-code", "s1"), got)
        self.assertNotIn(("claude-code", "s2"), got)
        self.assertIn(("antigravity", "conv1"), got)
        self.assertNotIn(("antigravity", "conv2"), got)
        self.assertIn(("opencode", "ses_1"), got)
        self.assertNotIn(("opencode", "ses_2"), got)
        self.assertEqual(len([g for g in got if g[0] == "codex"]), 1)

    def test_zip_is_redacted_and_excludes_credentials(self):
        self.make_all()
        sessions, _ = o.collect_all(self.ctx)
        out = self.repo / "agent-trace.zip"
        res = o.build_zip(self.ctx, sessions, out, keep_paths=False)
        z = zipfile.ZipFile(str(out))
        names = z.namelist()
        self.assertTrue(any(n.endswith("claude-code/" + re.sub(r"[^A-Za-z0-9]", "-", str(self.repo)) + "/s1.jsonl") for n in names))
        self.assertIn("agent-trace/MANIFEST.json", names)
        self.assertFalse(any("mcp_config" in n for n in names))
        self.assertIn("agent-trace/windsurf/export.md", names)
        blob = b"".join(z.read(n) for n in names).decode("utf-8", "replace")
        self.assertNotIn(SECRET, blob)
        self.assertNotIn(GH, blob)
        self.assertNotIn("/Users/%s/" % USER, blob)
        self.assertIn("/Users/<user>/", blob)
        self.assertGreaterEqual(res["redactions"].get("anthropic-key", 0), 1)
        orig = (self.home / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(self.repo)) / "s1.jsonl").read_text()
        self.assertIn(SECRET, orig)
        for n in names:
            if n.endswith(".jsonl"):
                for line in z.read(n).decode().splitlines():
                    json.loads(line)

    def test_symlinks_not_followed(self):
        self.make_all()
        secret = self.other / "secret.txt"
        secret.write_text("TOPSECRET")
        link = self.home / ".gemini" / "antigravity" / "brain" / "conv1" / "leak.txt"
        try:
            os.symlink(str(secret), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        sessions, _ = o.collect_all(self.ctx)
        out = self.repo / "agent-trace.zip"
        o.build_zip(self.ctx, sessions, out, False)
        z = zipfile.ZipFile(str(out))
        self.assertFalse(any("leak.txt" in n for n in z.namelist()))

    def test_empty_home_is_fine(self):
        sessions, diags = o.collect_all(self.ctx)
        self.assertEqual([s for s in sessions if s.files or s.blobs], [])
        self.assertIn("claude-code", diags)

    def test_since_filter(self):
        self.make_all()
        ctx = o.Ctx(self.repo, home=self.home, env=self.env, since=4102444800)  # year 2100
        sessions, _ = o.collect_all(ctx)
        self.assertEqual([s.harness for s in sessions if s.harness != "manual"], [])

    def test_only_filter(self):
        self.make_all()
        sessions, _ = o.collect_all(self.ctx, ["codex"])
        self.assertEqual({s.harness for s in sessions}, {"codex"})

    def test_truncated_jsonl_warns_but_copies(self):
        self.make_all()
        p = self.home / ".codex" / "sessions" / "2026" / "11" / "27" / "rollout-abc.jsonl"
        with open(str(p), "a") as f:
            f.write('{"half": ')
        sessions, _ = o.collect_all(self.ctx, ["codex"])
        res = o.build_zip(self.ctx, sessions, self.repo / "agent-trace.zip", True)
        self.assertTrue(any("not valid JSON" in w["warning"] for w in res["warnings"]))
        self.assertEqual(res["files"], 1)


class RedactTests(unittest.TestCase):
    def test_patterns(self):
        cases = {
            "sk-proj-" + "x" * 40: "[REDACTED]",
            "AKIAABCDEFGHIJKLMNOP": "[REDACTED]",
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123": "Bearer [REDACTED]",
            'postgres://user:pa55w0rd@db.example.com/x': "postgres://[REDACTED]@db.example.com/x",
        }
        for src, want in cases.items():
            self.assertIn(want, o.redact_text(src)[0], src)
        t, _ = o.redact_text('{"api_key": "abcdefgh12345678"}')
        self.assertIn('"api_key": "[REDACTED]"', t)
        t, _ = o.redact_text('{\\"password\\": \\"hunter2hunter2\\"}')
        self.assertNotIn("hunter2hunter2", t)
        t, _ = o.redact_text("api_key = os.getenv('X')")
        self.assertIn("os.getenv", t)
        t, _ = o.redact_text("-----BEGIN RSA PRIVATE KEY-----\\nMIIabc\\n-----END RSA PRIVATE KEY-----")
        self.assertEqual(t, "[REDACTED]")

    def test_secret_filenames(self):
        for n in ("auth.json", ".env", ".env.local", "mcp.json", "mcp_config.json", "config.toml", "id_rsa", "settings.json"):
            self.assertTrue(o.is_secret_name(n), n)
        for n in ("rollout-1.jsonl", "transcript_full.jsonl", "walkthrough.md", "session-1.json"):
            self.assertFalse(o.is_secret_name(n), n)


GOOD_STEP = {"step_no": 1, "phase": "FINDING", "system_id": "s", "resource_id": "r",
             "operation": "REPORT_REMAINING_RECORD", "state": "PRESENT", "evidence_id": "evidence_01"}


class OutputTests(Fixture):
    def write(self, rows, ids=("c1", "c2"), header=("case_id", "deletion_status", "steps_json")):
        (self.repo / "dataset").mkdir(exist_ok=True)
        with open(str(self.repo / "dataset" / "deletion_requests.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["case_id", "email"])
            for i in ids:
                w.writerow([i, "x"])
        with open(str(self.repo / "output.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    def test_valid(self):
        self.write([["c1", "NOT_APPLICABLE", "[]"], ["c2", "INCOMPLETE", json.dumps([GOOD_STEP])]])
        errs, _, stats = o.check_output(self.repo)
        self.assertEqual(errs, [])
        self.assertEqual(stats, {"NOT_APPLICABLE": 1, "INCOMPLETE": 1})

    def test_problems(self):
        bad = dict(GOOD_STEP, step_no=2)
        wrong_state = dict(GOOD_STEP, state="ACTIVE")
        extra = dict(GOOD_STEP, foo=1)
        for steps, frag in [([bad], "consecutive"), ([wrong_state], "requires state"), ([extra], "wrong fields")]:
            self.write([["c1", "NOT_APPLICABLE", "[]"], ["c2", "INCOMPLETE", json.dumps(steps)]])
            errs, _, _ = o.check_output(self.repo)
            self.assertTrue(any(frag in e for e in errs), (frag, errs))
        self.write([["c2", "NOT_APPLICABLE", "[]"], ["c1", "NOT_APPLICABLE", "[]"]])
        self.assertTrue(any("not sorted" in e for e in o.check_output(self.repo)[0]))
        self.write([["c1", "NOT_APPLICABLE", "[1]"], ["c2", "MAYBE", "[]"]])
        errs = o.check_output(self.repo)[0]
        self.assertTrue(any("requires steps_json=[]" in e for e in errs))
        self.assertTrue(any("deletion_status" in e for e in errs))
        self.write([["c1", "NOT_APPLICABLE", "[]"]])
        self.assertTrue(any("expected 2 data rows" in e for e in o.check_output(self.repo)[0]))
        self.write([["c1", "NOT_APPLICABLE", "[]"], ["c2", "NOT_APPLICABLE", "[]"]], header=("case_id", "status", "steps_json"))
        self.assertTrue(any("header" in e for e in o.check_output(self.repo)[0]))

    def test_phase_order(self):
        v = dict(GOOD_STEP, step_no=1, phase="VERIFICATION", operation="VERIFY_RECORD_ABSENT", state="ABSENT")
        f = dict(GOOD_STEP, step_no=2)
        self.write([["c1", "NOT_APPLICABLE", "[]"], ["c2", "INCOMPLETE", json.dumps([v, f])]])
        self.assertTrue(any("out of order" in e for e in o.check_output(self.repo)[0]))

    def test_missing_file(self):
        self.assertTrue(any("not found" in e for e in o.check_output(self.repo)[0]))


class LogTests(Fixture):
    def run_log(self, *argv, stdin=None):
        args = o.build_parser().parse_args(["log"] + list(argv))
        old = sys.stdin
        if stdin is not None:
            sys.stdin = type("S", (), {"buffer": io.BytesIO(stdin.encode())})()
        try:
            return o.cmd_log(args, self.ctx)
        finally:
            sys.stdin = old

    def test_validators(self):
        for bad in ("", "AI", "unknown", "<tool>", "claude-sonnet-5-5"):
            self.assertIsNotNone(o.validate_tool(bad), bad)
        for good in ("Claude Code", "Codex CLI", "OpenCode", "Antigravity", "Cursor"):
            self.assertIsNone(o.validate_tool(good), good)
        for bad in ("", "unknown", "claude", "sonnet", "<model>", "auto"):
            self.assertIsNotNone(o.validate_model(bad), bad)
        for good in ("claude-sonnet-5-5", "gpt-5", "o3", "gemini-3-pro"):
            self.assertIsNone(o.validate_model(good), good)

    def test_start_and_turn_then_check_log(self):
        self.assertEqual(self.run_log("start", "--tool", "Claude Code", "--model", "claude-sonnet-5-5"), 0)
        self.assertEqual(self.run_log("turn", "--tool", "Claude Code", "--model", "claude-sonnet-5-5", "--title", "t" * 120,
                                      "--summary", "Did a thing.", "--action", "edited a.py",
                                      "--prompt-stdin", stdin="my key %s\nsecond line" % SECRET), 0)
        text = (self.repo / "log.txt").read_text()
        self.assertNotIn(SECRET, text)
        self.assertIn("SESSION START", text)
        self.assertEqual(len(re.findall(r"(?m)^## \[.*\] t{80}$", text)), 1)
        self.assertEqual(o.check_log(self.repo), [])

    def test_rejects_bad_identity_and_writes_nothing(self):
        self.assertEqual(self.run_log("start", "--tool", "AI", "--model", "claude-sonnet-5-5"), 2)
        self.assertEqual(self.run_log("start", "--tool", "Claude Code", "--model", "unknown"), 2)
        self.assertFalse((self.repo / "log.txt").exists())

    def test_check_log_flags_bad_entry(self):
        (self.repo / "log.txt").write_text("## [2026-01-01T00:00:00+00:00] SESSION START\n\ntool=AI\nmodel=unknown\n")
        self.assertTrue(len(o.check_log(self.repo)) >= 2)


if __name__ == "__main__":
    unittest.main()


class ArcNameTests(Fixture):
    def test_username_masked_in_entry_names(self):
        r = Path(self.tmp.name).resolve() / "Users" / USER / "proj"
        r.mkdir(parents=True)
        ctx = o.Ctx(r, home=self.home, env=self.env)
        enc = re.sub(r"[^A-Za-z0-9]", "-", str(r))
        jl(self.home / ".claude" / "projects" / enc / "s1.jsonl", {"cwd": str(r)})
        sessions, _ = o.collect_all(ctx)
        o.build_zip(ctx, sessions, r / "agent-trace.zip", False)
        names = zipfile.ZipFile(str(r / "agent-trace.zip")).namelist()
        self.assertFalse(any("Users-%s" % USER in n for n in names), names)
        self.assertTrue(any("Users-user" in n for n in names), names)
