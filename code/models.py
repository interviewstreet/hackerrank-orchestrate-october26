"""
models.py — shared dataclasses for the Ghost Data Still Exists pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


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
