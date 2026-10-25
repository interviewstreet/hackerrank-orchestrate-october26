"""Rule-based intent: does the request text authorise deletion?

DELETE   a deletion verb or noun is present and nothing protects the account
OTHER    the text protects the account or disclaims deletion (even if a delete verb appears,
         e.g. "without removing", "do not close", "not a request to erase")
UNSURE   neither signal; sent to the model fallback
"""
from __future__ import annotations

import re

DELETE, OTHER, UNSURE = "DELETE", "OTHER", "UNSURE"

_DELETE_PATTERNS = [
    # English
    r"\bdelet(e|ed|es|ing|ion)\b", r"\beras(e|ed|ure|ing)\b", r"\bremov(e|ed|al|ing)\b",
    r"\bclos(e|ed|ing)\b[^.]{0,40}\baccount\b", r"\baccount\b[^.]{0,40}\bclosed\b",
    r"\bpermanent(ly)?\b[^.]{0,30}\b(delet|eras|remov)", r"\bforget me\b",
    # Spanish, Portuguese, French
    r"\belimina(r|ción|cion|do|da)\b", r"\bborr(ar|ado)\b",
    r"\bexclus[ãa]o\b", r"\bexclu(ir|ído|ida)\b", r"\bapag(ar|ado)\b",
    r"\bsuppression\b", r"\bsupprim(er|é|ée)\b", r"\beffac(er|ement)\b",
    # Japanese, Korean
    r"削除", r"消去", r"삭제", r"탈퇴",
]

_PROTECT_PATTERNS = [
    r"\bnot (asking for|a request (for|to))\b[^.]{0,20}\b(delet|eras|remov)",
    r"\b(do not|don't|dont|never)\s+(close|delete|erase|remove)\b",
    r"\bwithout (removing|deleting|erasing|closing)\b",
    r"\b(leave|keep)\b[^.]{0,30}\b(account|profile)\b[^.]{0,25}\b(active|as it is|in place|open)\b",
    r"\b(leave|keep) the account\b",
    r"\bmarketing (lists?|emails?) only\b",
    r"\bcontinue using\b",
    r"\bstill (want|need|use)\b[^.]{0,30}\b(account|receipts|service|it)\b",
]

_DELETE_RE = [re.compile(p, re.IGNORECASE) for p in _DELETE_PATTERNS]
_PROTECT_RE = [re.compile(p, re.IGNORECASE) for p in _PROTECT_PATTERNS]


def classify(text: str) -> tuple[str, str]:
    """Return (label, reason)."""
    t = " ".join(text.replace("’", "'").split())
    for rx in _PROTECT_RE:
        m = rx.search(t)
        if m:
            return OTHER, f"protects account: {m.group(0)!r}"
    for rx in _DELETE_RE:
        m = rx.search(t)
        if m:
            return DELETE, f"deletion signal: {m.group(0)!r}"
    return UNSURE, "no deletion or protection signal"
