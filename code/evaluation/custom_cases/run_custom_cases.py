#!/usr/bin/env python3
"""Custom evaluation cases (synthetic, in-memory overlays).

Each case drives the real pipeline components (intent classifier, fact
store, state reconstructor, planner) with a tiny hand-built fact set, so
the behaviour is checked end-to-end without touching dataset/.

Run: python3 code/evaluation/custom_cases/run_custom_cases.py
Exit code 0 iff every case passes.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from audit.facts import FactStore                       # noqa: E402
from audit.intent import classify_rule                  # noqa: E402
from audit.planner import build_steps                   # noqa: E402
from audit.state import StateReconstructor              # noqa: E402

AUDIT = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
BEFORE = datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc)
AFTER = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
RESULTS = []


def report(cid, name, ok, detail=""):
    RESULTS.append(ok)
    print(f"{cid} {name}: {'PASS' if ok else 'FAIL'} {detail}")


def make_store():
    store = FactStore()
    store.current_manifest = BEFORE  # evidence file captured before audit
    return store


def ids_for(email, extra_emails=()):
    return {"emails": {email, *extra_emails}, "hashes": set(),
            "phones": set(), "user_ids": set(), "name": ""}


def run_case(store, ids, intent="DELETE"):
    states = StateReconstructor(store).evaluate_case(ids, AUDIT, [])
    return build_steps(intent, states)


# C1: non-deletion wording (incl. multilingual) must be NOT_APPLICABLE,
#     while genuine deletion wording in other languages stays DELETE.
c1a = classify_rule("Please do not delete my account; I just need a copy "
                    "of the information held on my account.")
c1b = classify_rule("Por favor eliminar mi cuenta permanentemente.")
c1c = classify_rule("계정 삭제를 요청합니다.")
report("C1", "intent: negation vs multilingual deletion",
       c1a["intent"] == "NON_DELETE" and c1b["intent"] == "DELETE"
       and c1c["intent"] == "DELETE",
       f"({c1a['intent']}, {c1b['intent']}, {c1c['intent']})")

# C2: leftover search document reachable only via the OLD (historical)
#     email must still be found and reported.
store = make_store()
store.add("evidence_01", "evidence", BEFORE, "search_service", "search_9001",
          "SEARCH_INDEX_ENTRY", "PRESENT", record={"email": "old@example.com"})
status, steps = run_case(store, ids_for("new@example.com",
                                        extra_emails={"old@example.com"}))
ops = {(s["phase"], s["resource_id"], s["operation"]) for s in steps}
report("C2", "historical-email leftover is a finding",
       status == "INCOMPLETE"
       and ("FINDING", "search_9001", "REPORT_REMAINING_RECORD") in ops,
       f"(status={status})")

# C3: a leftover that only appears in evidence timestamped AFTER audit_at
#     must not change the verdict, and nothing post-audit may be cited.
store = make_store()
store.add("evidence_01", "evidence", BEFORE, "search_service", "search_9002",
          "SEARCH_INDEX_ENTRY", "ABSENT",
          emails={"person@example.com"})  # lookup was for this subject
store.current_manifest = AFTER
store.add("evidence_02", "evidence", AFTER, "search_service", "search_9002",
          "SEARCH_INDEX_ENTRY", "PRESENT",
          record={"email": "person@example.com"})
status, steps = run_case(store, ids_for("person@example.com"))
report("C3", "post-audit evidence ignored",
       status == "COMPLETE" and len(steps) == 1
       and steps[0]["evidence_id"] == "evidence_01",
       f"(status={status}, steps={steps})")

# C4: a tombstone that still carries an email hash is exposed; a tombstone
#     with only the stable user reference is compliant.
store = make_store()
store.add("evidence_01", "evidence", BEFORE, "account_service",
          "tombstone_9001", "ACCOUNT_TOMBSTONE", "PRESENT",
          record={"user_id": "user_99", "email_hash": "a" * 64})
status, steps = run_case(store, {"emails": set(), "hashes": set(),
                                 "phones": set(), "user_ids": {"user_99"},
                                 "name": ""})
bad_ops = {(s["phase"], s["operation"]) for s in steps}
store = make_store()
store.add("evidence_01", "evidence", BEFORE, "account_service",
          "tombstone_9002", "ACCOUNT_TOMBSTONE", "PRESENT",
          record={"user_id": "user_98"})
status2, steps2 = run_case(store, {"emails": set(), "hashes": set(),
                                   "phones": set(),
                                   "user_ids": {"user_98"}, "name": ""})
report("C4", "tombstone: hash exposed, user_id-only compliant",
       status == "INCOMPLETE"
       and ("REMEDIATION", "REDACT_RECORD") in bad_ops
       and status2 == "COMPLETE",
       f"(exposed->{status}, clean->{status2})")

# C5: restorable backup is a restore risk; a blocked backup is compliant.
def backup_case(restore_allowed):
    store = make_store()
    store.add("evidence_01", "evidence", BEFORE, "backup_service",
              "backup_9001", "BACKUP_ARCHIVE", "PRESENT",
              record={"owner_email": "person@example.com"},
              restore_allowed=restore_allowed)
    return run_case(store, ids_for("person@example.com"))

status_r, steps_r = backup_case(True)
status_b, steps_b = backup_case(False)
report("C5", "backup restore risk vs blocked",
       status_r == "INCOMPLETE"
       and any(s["operation"] == "REPORT_RESTORE_RISK" for s in steps_r)
       and any(s["operation"] == "BLOCK_RESTORE" for s in steps_r)
       and status_b == "COMPLETE"
       and any(s["operation"] == "VERIFY_RESTORE_BLOCKED" for s in steps_b),
       f"(restorable->{status_r}, blocked->{status_b})")

# C6: an UPPERCASE email in evidence still links to the subject.
store = make_store()
store.add("evidence_01", "evidence", BEFORE, "search_service", "search_9003",
          "SEARCH_INDEX_ENTRY", "PRESENT",
          record={"email": "PERSON@EXAMPLE.COM"})
status, steps = run_case(store, ids_for("person@example.com"))
report("C6", "uppercase email in evidence links",
       status == "INCOMPLETE"
       and any(s["resource_id"] == "search_9003" for s in steps),
       f"(status={status})")

print(f"\n{sum(RESULTS)}/{len(RESULTS)} custom cases passed")
sys.exit(0 if all(RESULTS) else 1)
