"""As-of identity resolution.

Resolve a request email to a ``user_id`` and collect every current and historical
identifier (emails, phones, names, email hashes) that was known at ``as_of``
(inclusive). Audit-log changes after ``as_of`` are never used: if a field changed
later, the value at ``as_of`` is the ``old_value`` of the earliest later change, and
the later values are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from loaders import AuditEntry, Dataset, Identity, email_hash, normalize_email, normalize_phone

TRACKED_FIELDS = ("email", "phone", "email_hash")


class FutureDataError(RuntimeError):
    """Raised when resolution would use identity data dated after ``as_of``."""


@dataclass
class SubjectIdentity:
    user_id: str
    as_of: datetime
    matched_via: str                     # "current" | "historical"
    name: str
    current_email: str
    current_phone: str
    current_email_hash: str
    emails: list[str] = field(default_factory=list)        # current first, then historical (sorted)
    phones: list[str] = field(default_factory=list)
    phone_digits: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    email_hashes: list[str] = field(default_factory=list)  # recorded + SHA-256 of every email
    audit_ids: list[str] = field(default_factory=list)     # audit rows used (all <= as_of)
    flags: list[str] = field(default_factory=list)

    @property
    def historical_emails(self) -> list[str]:
        return [e for e in self.emails if e != self.current_email]


@dataclass
class _FieldView:
    current: str
    known: list[str]
    used: list[AuditEntry]


class IdentityIndex:
    def __init__(self, data: Dataset):
        self.snapshot: dict[str, Identity] = {i.user_id: i for i in data.identities}
        self.changes: dict[str, list[AuditEntry]] = {}
        for entry in sorted(data.audit_log, key=lambda e: (e.event_time, e.audit_id)):
            self.changes.setdefault(entry.user_id, []).append(entry)
        # Every email ever seen for a user (any time); candidates are filtered as-of later.
        self._email_users: dict[str, set[str]] = {}
        for ident in data.identities:
            self._email_users.setdefault(ident.email, set()).add(ident.user_id)
        for entry in data.audit_log:
            if entry.field_name == "email":
                for value in (entry.old_value, entry.new_value):
                    if value:
                        self._email_users.setdefault(value, set()).add(entry.user_id)

    # ------------------------------------------------------------ as-of view

    def _field_view(self, user_id: str, field_name: str, as_of: datetime) -> _FieldView:
        snap_value = getattr(self.snapshot[user_id], field_name) if user_id in self.snapshot else ""
        entries = [e for e in self.changes.get(user_id, []) if e.field_name == field_name]
        past = [e for e in entries if e.event_time <= as_of]
        future = [e for e in entries if e.event_time > as_of]
        current = future[0].old_value if future else snap_value
        known: list[str] = []
        for value in [current] + [v for e in reversed(past) for v in (e.new_value, e.old_value)]:
            if value and value not in known:
                known.append(value)
        return _FieldView(current, known, past)

    def user_ids_for_email(self, email: str, as_of: datetime) -> list[str]:
        """Users whose email (current or historical) at ``as_of`` equals ``email``."""
        email = normalize_email(email)
        hits = []
        for user_id in sorted(self._email_users.get(email, ())):
            if email in self._field_view(user_id, "email", as_of).known:
                hits.append(user_id)
        return hits

    def subject(self, user_id: str, as_of: datetime, matched_via: str = "current") -> SubjectIdentity:
        if user_id not in self.snapshot:
            raise KeyError(f"unknown user_id {user_id}")
        snap = self.snapshot[user_id]
        views = {f: self._field_view(user_id, f, as_of) for f in TRACKED_FIELDS}
        used = sorted({e for v in views.values() for e in v.used}, key=lambda e: (e.event_time, e.audit_id))
        late = [e.audit_id for e in used if e.event_time > as_of]
        if late:  # guard: the as-of view must never include later audit rows
            raise FutureDataError(f"{user_id}: audit rows after {as_of.isoformat()}: {late}")

        flags = []
        if any(e.event_time > as_of for e in self.changes.get(user_id, [])):
            flags.append("future_changes_ignored")
        if snap.updated_at > as_of:
            flags.append("snapshot_updated_after_as_of")

        emails = views["email"].known
        emails = [emails[0], *sorted(emails[1:])] if emails else []
        phones = views["phone"].known
        phones = [phones[0], *sorted(phones[1:])] if phones else []
        hashes: list[str] = []
        for value in views["email_hash"].known + [email_hash(e) for e in emails]:
            if value and value not in hashes:
                hashes.append(value)
        cur_hash = views["email_hash"].current or (email_hash(emails[0]) if emails else "")
        if views["email"].current and email_hash(views["email"].current) != cur_hash:
            flags.append("email_hash_mismatch")

        return SubjectIdentity(
            user_id=user_id,
            as_of=as_of,
            matched_via=matched_via,
            name=snap.name,
            current_email=views["email"].current,
            current_phone=views["phone"].current,
            current_email_hash=cur_hash,
            emails=emails,
            phones=phones,
            phone_digits=sorted({normalize_phone(p) for p in phones if p}),
            names=[snap.name] if snap.name else [],
            email_hashes=hashes,
            audit_ids=[e.audit_id for e in used],
            flags=flags,
        )

    def resolve(self, email: str, as_of: datetime) -> SubjectIdentity | None:
        """Resolve a request email at ``as_of``. Returns None when no user matches."""
        email = normalize_email(email)
        candidates = self.user_ids_for_email(email, as_of)
        if not candidates:
            return None
        current = [u for u in candidates if self._field_view(u, "email", as_of).current == email]
        chosen = (current or candidates)[0]
        result = self.subject(chosen, as_of, "current" if current else "historical")
        if len(candidates) > 1:
            result.flags.append("ambiguous_email:" + ",".join(candidates))
        return result
