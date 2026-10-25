"""Plain-text handover evidence: `ts | system | resource | TYPE | RESULT | id`."""
import re

from ..loaders import parse_ts

_LINE = re.compile(
    r"^-\s*(\S+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*(.+)$")


def parse_text_content(text, source_id, store, manifest_ts):
    before = len(store.facts)
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        ts, system, resource, rtype, result, subject = (
            g.strip() for g in m.groups())
        result_u = result.upper()
        subject_l = subject.lower()
        emails = {subject_l} if "@" in subject_l else None
        users = {subject} if subject.startswith("user_") else None
        presence = "ABSENT" if result_u == "NOT_FOUND" else "PRESENT"
        enabled = (result_u == "ACTIVE") if rtype == "DATA_FLOW" else None
        restore = None
        if rtype == "BACKUP_ARCHIVE":
            restore = {"ACTIVE": True, "BLOCKED": False}.get(result_u)
        exposed = result_u == "IDENTIFIABLE"
        attributable = exposed
        rec = None
        if presence == "PRESENT" and emails:
            rec = {"email": subject_l}
        store.add(source_id, "evidence", parse_ts(ts) or manifest_ts,
                  system, resource, rtype, presence, record=rec,
                  emails=emails, user_ids=users, enabled=enabled,
                  restore_allowed=restore,
                  exposed=exposed if presence == "PRESENT" else False,
                  attributable=attributable if presence == "PRESENT" else False)
    return len(store.facts) - before
