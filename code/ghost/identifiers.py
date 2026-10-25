"""Identifier normalisation shared by the identity table and every evidence parser.

Both sides must normalise identically, otherwise an exact-match lookup silently misses.
"""
from __future__ import annotations

import hashlib
import re

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_USER_ID_RE = re.compile(r"\buser_\d+\b")
_HASH_RE = re.compile(r"\b[0-9a-fA-F]{64}\b")
_NON_DIGIT = re.compile(r"\D")


def norm_email(value: str) -> str:
    return value.strip().lower()


def norm_phone(value: str) -> str:
    """'+82 10 8980 7924', '+82-10-8980-7924' and '+821089807924' all become '+821089807924'."""
    digits = _NON_DIGIT.sub("", value)
    return f"+{digits}" if digits else ""


def norm_hash(value: str) -> str:
    return value.strip().lower()


def email_hash(email: str) -> str:
    """The dataset's email_hash is SHA-256 of the lower-cased email (verified on all users)."""
    return hashlib.sha256(norm_email(email).encode("utf-8")).hexdigest()


def normalise(kind: str, value: str) -> str:
    if kind == "email":
        return norm_email(value)
    if kind == "phone":
        return norm_phone(value)
    if kind in ("hash", "email_hash"):
        return norm_hash(value)
    return value.strip()


def find_identifiers(text: str) -> set[str]:
    """Pull every email, user_id and 64-hex hash out of free text, normalised.

    Word boundaries on user ids stop 'user_38' from matching inside 'user_388'.
    Phones are not scraped from free text (too many false positives); parsers pass
    phone fields explicitly through norm_phone.
    """
    found = {norm_email(m) for m in _EMAIL_RE.findall(text)}
    found.update(_USER_ID_RE.findall(text))
    found.update(norm_hash(m) for m in _HASH_RE.findall(text))
    return found
