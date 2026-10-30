"""Identity resolution: request email -> stable user_id plus every current and historical identifier."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from .loaders import email_hash, normalize_email, normalize_phone, normalize_text
from .models import AuditEntry, Identity


@dataclass(frozen=True)
class Subject:
    user_id: str | None
    identifiers: frozenset            # {(type, normalized value)}
    names: frozenset = frozenset()    # lower-cased names (used for exposure checks, never for linking)
    history: tuple = field(default_factory=tuple)  # (field, old, new, at, audit_id)

    def values(self, kind: str) -> set[str]:
        return {v for k, v in self.identifiers if k == kind}


def norm_identifier(kind: str, value: str) -> tuple[str, str] | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v or v.lower() in {"null", "none", "[redacted]"}:
        return None
    if kind == "email":
        return ("email", normalize_email(v))
    if kind == "phone":
        p = normalize_phone(v)
        return ("phone", p) if len(p.strip("+")) >= 6 else None
    if kind == "email_hash":
        return ("email_hash", v.lower())
    if kind == "user_id":
        return ("user_id", v.lower())
    if kind == "name":
        return ("name", " ".join(normalize_text(v).split()))
    return (kind, v)


class IdentityResolver:
    def __init__(self, identities: list[Identity], audit_log: list[AuditEntry]):
        self.identities = {i.user_id: i for i in identities}
        self.history: dict[str, list[AuditEntry]] = defaultdict(list)
        # an entry with an unreadable time keeps its identifiers; it sorts first and never moves a holding
        for a in sorted(audit_log, key=lambda a: (a.event_time is not None, a.event_time or 0, a.audit_id)):
            self.history[a.user_id].append(a)
        # email -> [(user_id, held_from, held_until)]
        self._email_index: dict[str, set[str]] = defaultdict(set)
        for uid, ident in self.identities.items():
            self._email_index[normalize_email(ident.email)].add(uid)
        for uid, entries in self.history.items():
            for a in entries:
                if a.field_name == "email":
                    for v in (a.old_value, a.new_value):
                        if v:
                            self._email_index[normalize_email(v)].add(uid)

    def candidates(self, email: str) -> list[str]:
        return sorted(self._email_index.get(normalize_email(email), set()))

    def _held_at(self, uid: str, email: str, at: datetime) -> bool:
        """True when `uid` held `email` at time `at` according to the audit history."""
        e = normalize_email(email)
        current = normalize_email(self.identities[uid].email)
        held = current
        for a in reversed(self.history.get(uid, [])):
            if a.field_name == "email" and a.event_time is not None and a.event_time > at:
                held = normalize_email(a.old_value)
        return held == e or (current == e and not self.history.get(uid))

    def subject_for_user(self, uid: str) -> Subject:
        ident = self.identities[uid]
        ids: set = set()
        names: set = set()
        for kind, val in (("email", ident.email), ("phone", ident.phone), ("email_hash", ident.email_hash), ("user_id", uid)):
            n = norm_identifier(kind, val)
            if n:
                ids.add(n)
        if ident.name:
            names.add(" ".join(normalize_text(ident.name).split()))
        hist = []
        for a in self.history.get(uid, []):
            hist.append((a.field_name, a.old_value, a.new_value, a.event_time.isoformat() if a.event_time else None, a.audit_id))
            for v in (a.old_value, a.new_value):
                kind = {"email": "email", "phone": "phone", "email_hash": "email_hash", "name": "name"}.get(a.field_name)
                if kind == "name":
                    if v:
                        names.add(" ".join(normalize_text(v).split()))
                    continue
                n = norm_identifier(kind, v) if kind else None
                if n:
                    ids.add(n)
        # every email also yields its sha256 hash
        for kind, val in list(ids):
            if kind == "email":
                ids.add(("email_hash", email_hash(val)))
        return Subject(uid, frozenset(ids), frozenset(names), tuple(hist))

    def resolve(self, email: str, as_of: datetime | None = None) -> Subject | None:
        cands = self.candidates(email)
        if not cands:
            return None
        if len(cands) > 1 and as_of is not None:
            holders = [u for u in cands if self._held_at(u, email, as_of)]
            if len(holders) == 1:
                cands = holders
        return self.subject_for_user(cands[0])

    def bare_subject(self, email: str) -> Subject:
        e = normalize_email(email)
        return Subject(None, frozenset({("email", e), ("email_hash", email_hash(e))}))
