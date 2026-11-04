"""
models.py — shared dataclasses for the Ghost Data Still Exists pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# P2 -> P3 contract: keys of the dict returned by evidence_search.find_records()
# (see code/CONTRACTS.md, section 1)
# ---------------------------------------------------------------------------
EVIDENCE_KEYS: tuple[str, ...] = (
    "records",                # list[ObservedRecord]
    "latest_by_resource",     # dict[(system_id, resource_id, replica_or_table), ObservedRecord]
    "referenced_resources",   # list[dict]: resources linked to the subject without a direct identifier
    "absence_proofs",         # dict[(system_id, resource_id), list[AbsenceProof]]
    "identifier_provenance",  # dict[str, list[str]]: subject identifier -> evidence/audit ids where it matched
)


def empty_evidence() -> dict:
    """A P2 -> P3 dict with every key present and nothing found."""
    return {
        "records": [],
        "latest_by_resource": {},
        "referenced_resources": [],
        "absence_proofs": {},
        "identifier_provenance": {},
    }


@dataclass(frozen=True)
class IdentityChange:
    """One row of user_audit_log.csv: a single identity-field change."""
    audit_id: str       # e.g. "audit_123" — cite this as evidence_id
    field_name: str     # "email" | "phone" | "email_hash"
    old_value: str
    new_value: str
    event_time: str     # ISO-8601 UTC string exactly as in the CSV, e.g. "2025-06-01T00:00:00Z"


@dataclass
class IdentityBundle:
    """All current and historical identifiers resolved for one deletion subject."""
    user_id: str
    current_email: str
    current_name: str
    current_phone: str
    current_email_hash: str
    # Historical values seen in user_audit_log (may be empty)
    historical_emails: list[str] = field(default_factory=list)
    historical_phones: list[str] = field(default_factory=list)
    historical_email_hashes: list[str] = field(default_factory=list)
    # The email that was supplied with the request (before normalisation)
    request_email: str = ""
    # Every audit-log change for this user at or before audit_at,
    # oldest first (ties broken by audit_id)
    history: list[IdentityChange] = field(default_factory=list)

    def all_emails(self) -> list[str]:
        """Return all known email addresses (current + historical), lower-cased."""
        result = [self.current_email.lower()]
        for e in self.historical_emails:
            e_low = e.lower()
            if e_low not in result:
                result.append(e_low)
        return result

    def all_email_hashes(self) -> list[str]:
        result = [self.current_email_hash]
        for h in self.historical_email_hashes:
            if h not in result:
                result.append(h)
        return result

    def all_phones(self) -> list[str]:
        result = [self.current_phone]
        for p in self.historical_phones:
            if p not in result:
                result.append(p)
        return result

    def as_subject_kwargs(self) -> dict:
        """
        Keyword arguments for P2's SubjectIdentifiers (code/evidence/models.py):

            SubjectIdentifiers(**identity.as_subject_kwargs())

        Returns exactly the 6 fields, as frozensets (user_id as str or None).
        Empty strings are dropped, so a missing phone or name never becomes
        a search term that matches every blank field in the evidence.
        """
        def fs(values) -> frozenset[str]:
            return frozenset(v for v in values if v and v.strip())

        return {
            "user_id": self.user_id or None,
            "emails": fs(self.all_emails()),
            "phones": fs(self.all_phones()),
            "email_hashes": fs(self.all_email_hashes()),
            "names": fs([self.current_name]),
            "resource_ids": frozenset(),
        }


class ClassificationResult:
    """Result of classifying a deletion request text."""
    IS_DELETION = "IS_DELETION"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNCERTAIN = "UNCERTAIN"

    def __init__(
        self,
        label: str,
        confidence: str,
        matched_keywords: list[str],
        note: str = "",
    ):
        assert label in (
            self.IS_DELETION,
            self.NOT_APPLICABLE,
            self.UNCERTAIN,
        ), f"Invalid label: {label!r}"
        self.label = label
        self.confidence = confidence        # "HIGH" | "LOW"
        self.matched_keywords = matched_keywords
        self.note = note

    def is_deletion(self) -> bool:
        return self.label == self.IS_DELETION

    def __repr__(self) -> str:
        return (
            f"ClassificationResult(label={self.label!r}, "
            f"confidence={self.confidence!r}, "
            f"keywords={self.matched_keywords!r}, "
            f"note={self.note!r})"
        )
