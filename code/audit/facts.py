"""Normalized fact store.

Every evidence parser emits ``Fact`` objects; all audit logic then runs on
facts, never on raw files. ``is_claim=True`` facts come from
system_activity.csv (workflow claims) and are used only for discovery/risk
hints -- they can never prove a resource state.
"""
import re
from dataclasses import dataclass, field

from .identity import norm_email, norm_phone

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
USER_RE = re.compile(r"\buser_\d+\b")
HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
RESOURCE_RE = re.compile(
    r"\b(account|search|analytics|support|export|data_flow|backup|audit_record|"
    r"tombstone|legal_hold|marketing|cache|email_delivery|object)_[\w\-]+\b")

# Fields that count as *direct* identifiers when evaluating exposure.
# Internal references (customer_reference / subject_reference holding a
# user_id, ticket ids, order ids) are deliberately excluded: a redacted
# support record and an account tombstone may keep such references.
DIRECT_EMAIL_KEYS = {"email", "owner_email", "requester_email", "customer_email",
                     "uploaded_by", "subject_selector", "lookup_value",
                     "owner", "billing_email"}
DIRECT_NAME_KEYS = {"full_name", "display_name", "requester_name", "name",
                    "customer_name"}
DIRECT_PHONE_KEYS = {"phone", "requester_phone", "owner_phone"}
DIRECT_HASH_KEYS = {"email_hash"}
DIRECT_USER_KEYS = {"user_id"}  # e.g. analytics profiles link via user_id
TEXT_BODY_KEYS = {"message_text", "message_excerpt", "message_body",
                  "body", "excerpt", "content", "message"}


@dataclass
class Fact:
    fact_id: str
    source_id: str          # evidence_xx | activity_xxxx | audit_xx
    source_kind: str        # "evidence" | "activity" | "audit"
    observed_at: object     # aware datetime or None
    system_id: str
    resource_id: str
    category: str
    presence: str           # PRESENT | ABSENT | UNKNOWN
    emails: frozenset = frozenset()
    user_ids: frozenset = frozenset()
    phones: frozenset = frozenset()
    hashes: frozenset = frozenset()
    names: frozenset = frozenset()
    exposed: bool = False       # a direct identifier is present in the record
    attributable: bool = False  # record can be linked to a person (incl. user ref in id fields)
    enabled: object = None      # data flows
    restore_allowed: object = None  # backups
    retention_until: object = None
    is_claim: bool = False
    detail: str = ""
    manifest_at: object = None  # evidence file captured_at (eligibility)

    def identifier_sets(self):
        return {"emails": set(self.emails), "hashes": set(self.hashes),
                "phones": set(self.phones), "user_ids": set(self.user_ids)}


def _bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def extract_identifiers(record):
    """Pull normalized identifiers out of an arbitrary record dict.

    Returns (emails, user_ids, phones, hashes, names, exposed, attributable).
    ``exposed`` tracks *direct* identifiers in the record's own identifier
    fields; ``attributable`` additionally covers an analytics-style user_id.
    """
    emails, users, phones, hashes, names = set(), set(), set(), set(), set()
    exposed = False

    def visit(obj, key_hint=""):
        nonlocal exposed
        if isinstance(obj, dict):
            for k, v in obj.items():
                visit(v, str(k))
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                visit(v, key_hint)
        elif isinstance(obj, str):
            s = obj.strip()
            if not s or s.lower() in ("null", "none"):
                return
            low = s.lower()
            found_emails = {m.group(0).lower() for m in EMAIL_RE.finditer(s)}
            emails.update(found_emails)
            users.update(USER_RE.findall(s))
            hashes.update(HASH_RE.findall(low))
            if key_hint in DIRECT_PHONE_KEYS:
                p = norm_phone(s)
                if len(p) >= 7:
                    phones.add(p)
            if key_hint in DIRECT_NAME_KEYS and not found_emails:
                names.add(low)
            # A support/e-mail message whose *body* still names an address
            # is exposed PII even though the body is not an id field.
            if key_hint in TEXT_BODY_KEYS and found_emails:
                exposed = True
            if key_hint in DIRECT_EMAIL_KEYS and found_emails:
                exposed = True
            if key_hint in DIRECT_PHONE_KEYS:
                exposed = True
            if key_hint in DIRECT_HASH_KEYS:
                exposed = True
            if key_hint in DIRECT_NAME_KEYS:
                exposed = True

    visit(record)
    # user_id held in a dedicated id field makes a record attributable, and
    # for identifier-bearing stores (analytics) it also counts as exposure.
    attributable = bool(emails or hashes or phones or names)

    def has_user_in_id_field(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k) in DIRECT_USER_KEYS and isinstance(v, str) \
                        and USER_RE.fullmatch(v.strip()):
                    return True
                if has_user_in_id_field(v):
                    return True
        return False

    if has_user_in_id_field(record):
        attributable = True
        exposed = True
    # subject/customer references (internal user_id) link but are not, on
    # their own, direct identifiers (tombstone/support may keep them).
    return emails, users, phones, hashes, names, exposed, attributable


class FactStore:
    def __init__(self):
        self.facts = []
        self.by_resource = {}
        self._counter = 0
        self.current_manifest = None  # set by the loader for each file

    def add(self, source_id, source_kind, observed_at, system_id, resource_id,
            category, presence, record=None, emails=None, user_ids=None,
            phones=None, hashes=None, names=None, exposed=None,
            attributable=None, enabled=None, restore_allowed=None,
            retention_until=None, is_claim=False, detail=""):
        if not resource_id:
            return None
        e, u, p, h, n = set(), set(), set(), set(), set()
        exp, attr = False, False
        if record is not None:
            e, u, p, h, n, exp, attr = extract_identifiers(record)
        if emails:
            e |= {norm_email(x) for x in emails if x}
        if user_ids:
            u |= set(user_ids)
        if phones:
            p |= {norm_phone(x) for x in phones if x}
        if hashes:
            h |= {str(x).lower() for x in hashes if x}
        if names:
            n |= {str(x).lower() for x in names if x}
        if exposed is None:
            exposed = exp
        if attributable is None:
            attributable = attr or exp
        if category == "ACCOUNT_TOMBSTONE":
            # A tombstone may keep only the stable user reference; any
            # direct identifier beyond that (email, hash, phone, name)
            # is exposure. The user_id alone never counts.
            exposed = bool(e or h or p or n)
        self._counter += 1
        fact = Fact(
            fact_id=f"{source_id}#{self._counter}", source_id=source_id,
            source_kind=source_kind, observed_at=observed_at,
            system_id=system_id or "", resource_id=str(resource_id),
            category=category or "", presence=presence,
            emails=frozenset(e), user_ids=frozenset(u), phones=frozenset(p),
            hashes=frozenset(h), names=frozenset(n), exposed=bool(exposed),
            attributable=bool(attributable), enabled=_bool(enabled),
            restore_allowed=_bool(restore_allowed),
            retention_until=retention_until, is_claim=is_claim, detail=detail,
            manifest_at=(self.current_manifest if source_kind == "evidence"
                         else observed_at))
        self.facts.append(fact)
        self.by_resource.setdefault(fact.resource_id, []).append(fact)
        return fact

    def facts_for_resource(self, resource_id):
        return self.by_resource.get(resource_id, [])
