"""Helpers shared by all format parsers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional

from ..models import ObservedRecord, ParseIssue, SnapshotScope, EvidenceFile
from ..normalize import (
    FILE_FIELDS,
    FREE_TEXT_FIELDS,
    HASH_FIELDS,
    NAME_FIELDS,
    PHONE_FIELDS,
    QUERY_KEY_FIELDS,
    RESOURCE_ID_RE,
    category_for,
    extract_emails,
    extract_file_names,
    extract_phones,
    extract_user_ids,
    is_nullish,
    norm_email,
    norm_hash,
    norm_name,
    norm_phone,
    norm_resource_id,
    norm_user_id,
)


@dataclass
class ParseResult:
    records: list[ObservedRecord] = field(default_factory=list)
    scopes: list[SnapshotScope] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def bump(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n


def clean_value(v: Any) -> Any:
    """Turn textual nulls into None and textual booleans into bools."""
    if isinstance(v, str):
        s = v.strip()
        low = s.lower()
        if low in ("null", "none", ""):
            return None
        if low == "true":
            return True
        if low == "false":
            return False
    return v


def _walk(payload: Any, path: str = ""):
    if isinstance(payload, dict):
        for k, v in payload.items():
            yield from _walk(v, k)
    elif isinstance(payload, list):
        for v in payload:
            yield from _walk(v, path)
    else:
        yield path, payload


def analyse_payload(payload: dict[str, Any], own_resource_id: str) -> tuple[dict[str, Any], Optional[str], set[tuple[str, str]]]:
    """Return (pii_fields, subject_reference, linked_terms) for a record payload.

    * pii_fields: direct identifiers stored *in* the record (non-null only).
    * subject_reference: a stable ``user_*`` reference carried by the record.
    * linked_terms: every normalised identifier usable to link the record to a
      subject, including query keys and cross-referenced resource ids.
    """
    pii: dict[str, Any] = {}
    subject_ref: Optional[str] = None
    terms: set[tuple[str, str]] = set()
    own = own_resource_id.lower()

    for key, raw in _walk(payload):
        key_l = (key or "").lower()
        v = clean_value(raw)
        if v is None or isinstance(v, bool) or isinstance(v, (int, float)):
            continue
        s = str(v)
        is_query = key_l in QUERY_KEY_FIELDS

        email = norm_email(s)
        if email:
            terms.add(("email", email))
            if not is_query:
                pii.setdefault(key_l, s)
            continue
        uid = norm_user_id(s)
        if uid:
            terms.add(("user_id", uid))
            if not is_query and subject_ref is None:
                subject_ref = uid
            continue
        if key_l in PHONE_FIELDS:
            p = norm_phone(s)
            if p:
                terms.add(("phone", p))
                pii.setdefault(key_l, s)
            continue
        if key_l in HASH_FIELDS or (is_query and len(s) == 64):
            h = norm_hash(s)
            if h:
                terms.add(("email_hash", h))
                if not is_query:
                    pii.setdefault(key_l, s)
                continue
        if key_l in NAME_FIELDS:
            n = norm_name(s)
            if n:
                terms.add(("name", n))
                pii.setdefault(key_l, s)
            continue
        if RESOURCE_ID_RE.fullmatch(s.strip()):
            rid = norm_resource_id(s)
            if rid and rid != own:
                terms.add(("resource_id", rid))
            continue
        if key_l in FILE_FIELDS:
            for fn in extract_file_names(s):
                terms.add(("file_name", fn))
            continue
        if key_l in FREE_TEXT_FIELDS or " " in s:
            found_e = extract_emails(s)
            found_p = extract_phones(s)
            for e in found_e:
                terms.add(("email", e))
            for p in found_p:
                terms.add(("phone", p))
            for u in extract_user_ids(s):
                terms.add(("user_id", u))
            if (found_e or found_p) and not is_query:
                pii.setdefault(key_l, s)
    terms.add(("resource_id", own))
    return pii, subject_ref, terms


def make_record(
    ev: EvidenceFile,
    *,
    system_id: str,
    resource_id: str,
    observed_at: datetime,
    presence: str,
    payload: dict[str, Any],
    claim_only: bool,
    source_format: str,
    locator: str,
    collection: Optional[str] = None,
    replica_or_table: Optional[str] = None,
    data_category: Optional[str] = None,
    raw_extra: Optional[dict[str, Any]] = None,
    extra_terms: Iterable[tuple[str, str]] = (),
    pii_override: Optional[dict[str, Any]] = None,
) -> ObservedRecord:
    rid = str(resource_id).strip()  # original casing preserved; indexes use lower()
    clean_payload = {k: clean_value(v) for k, v in payload.items()} if isinstance(payload, dict) else payload
    pii, subject_ref, terms = analyse_payload(clean_payload, rid)
    if pii_override is not None:
        pii = pii_override
    terms.update(extra_terms)
    raw_state = dict(clean_payload)
    if raw_extra:
        raw_state.update(raw_extra)
    return ObservedRecord(
        evidence_id=ev.file_id,
        system_id=system_id,
        resource_id=rid,
        data_category=data_category or category_for(collection, rid, system_id),
        collection=collection,
        replica_or_table=replica_or_table,
        observed_at=observed_at,
        captured_at=ev.captured_at,
        presence=presence,
        pii_fields=pii,
        identifiers_matched=[],
        raw_state=raw_state,
        claim_only=claim_only,
        source_format=source_format,
        locator=locator,
        subject_reference=subject_ref,
        linked_terms=frozenset(terms),
    )


def ledger_presence(result: Any) -> str:
    """Map a lookup-ledger ``result`` value to a presence."""
    from ..models import ABSENT, PRESENT, UNKNOWN

    r = str(result or "").strip().upper()
    if r in ("NOT_FOUND", "ABSENT", "MISS", "DELETED", "NONE"):
        return ABSENT
    if r in ("FOUND", "PRESENT", "HIT", "IDENTIFIABLE", "ANONYMIZED", "REDACTED",
             "ACTIVE", "DISABLED", "BLOCKED", "RETAINED"):
        return PRESENT
    return UNKNOWN
