"""Identity resolution: request email -> user, plus every identifier that provably belongs to that user.

Only exact matches are used (current email, historical email from the audit trail, stable user_id, email hash,
phone). Similar emails / names / usernames are never merged: lookalike addresses are different people.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .dataset_loader import DatasetContext, EmailSpan


@dataclass
class Subject:
    case_id: str
    request_email: str
    status: str                                   # RESOLVED | AMBIGUOUS | UNRESOLVED
    user_id: Optional[str] = None
    candidate_users: List[str] = field(default_factory=list)
    name: str = ""
    emails: List[str] = field(default_factory=list)           # every email the user has held
    email_spans: List[EmailSpan] = field(default_factory=list)
    hashes: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    matched_via: str = ""                                      # current_email | historical_email
    audit_ids: List[str] = field(default_factory=list)         # audit rows that prove historical identifiers
    confidence: float = 0.0

    def identifiers(self) -> List[Dict[str, str]]:
        out = [{"type": "user_id", "value": self.user_id}] if self.user_id else []
        for s in self.email_spans:
            out.append({"type": "email", "value": s.email, "valid_from": s.valid_from, "valid_to": s.valid_to,
                        "source": s.audit_id or "user_identities"})
        out += [{"type": "email_hash", "value": h} for h in self.hashes]
        out += [{"type": "phone", "value": p} for p in self.phones]
        return out


def resolve_subject(ctx: DatasetContext, case_id: str, email: str, audit_at: str = "") -> Subject:
    key = (email or "").strip().lower()
    users = ctx.users_for_email(key)
    if not users:
        return Subject(case_id, key, "UNRESOLVED")
    if len(users) > 1 and audit_at:
        # an address reused by several users: keep only users who held it before audit_at
        held = [u for u in users if any(s.email == key and (not s.valid_from or s.valid_from <= audit_at)
                                        for s in ctx.email_spans[u])]
        users = held or users
    if len(users) > 1:
        return Subject(case_id, key, "AMBIGUOUS", candidate_users=sorted(users))
    uid = users[0]
    ident = ctx.identities[uid]
    spans = [s for s in ctx.email_spans[uid] if not audit_at or not s.valid_from or s.valid_from <= audit_at]
    hashes = [h for h, u in ctx.hash_index.items() if uid in u]
    phones = [p for p, u in ctx.phone_index.items() if uid in u]
    via = "current_email" if ctx.current_email_index.get(key) == [uid] else "historical_email"
    return Subject(
        case_id=case_id, request_email=key, status="RESOLVED", user_id=uid, candidate_users=[uid], name=ident["name"],
        emails=[s.email for s in spans], email_spans=spans, hashes=hashes, phones=phones, matched_via=via,
        audit_ids=[s.audit_id for s in spans if s.audit_id], confidence=1.0)
