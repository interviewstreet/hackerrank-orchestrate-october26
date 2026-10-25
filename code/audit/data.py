"""Loading of the tabular dataset files and identity resolution."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .evidence import norm_phone


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@dataclass
class Identity:
    user_id: str
    name: str
    emails: set = field(default_factory=set)
    phones: set = field(default_factory=set)
    hashes: set = field(default_factory=set)
    audit_ids: list = field(default_factory=list)  # audit_log rows that changed an identifier

    def idents(self) -> set:
        return {self.user_id} | self.emails | self.hashes | self.phones


def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


class IdentityIndex:
    """Current snapshot plus audit-log history, queryable by any past or present email."""

    def __init__(self, identities_rows, audit_rows):
        self.users = {}
        self.by_email = {}
        for r in identities_rows:
            ident = Identity(r["user_id"], r["name"])
            self._add_email(ident, r["email"])
            if r.get("email_hash"):
                ident.hashes.add(r["email_hash"].lower())
            p = norm_phone(r.get("phone", ""))
            if p:
                ident.phones.add(p)
            self.users[r["user_id"]] = ident
        self.audit_rows = sorted(audit_rows, key=lambda a: a["event_time"])
        for a in self.audit_rows:
            ident = self.users.get(a["user_id"])
            if not ident:
                continue
            ident.audit_ids.append(a)
            field_name = a["field_name"]
            for value in (a["old_value"], a["new_value"]):
                if not value:
                    continue
                if field_name == "email":
                    self._add_email(ident, value)
                elif field_name == "email_hash":
                    ident.hashes.add(value.lower())
                elif field_name == "phone":
                    p = norm_phone(value)
                    if p:
                        ident.phones.add(p)
        for ident in self.users.values():
            for e in ident.emails:
                self.by_email[e] = ident.user_id

    def _add_email(self, ident: Identity, email: str):
        e = email.strip().lower()
        ident.emails.add(e)
        ident.hashes.add(email_hash(e))

    def resolve(self, email: str) -> Identity | None:
        uid = self.by_email.get(email.strip().lower())
        return self.users.get(uid) if uid else None
