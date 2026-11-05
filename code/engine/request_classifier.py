"""Decide whether a request text actually authorizes deletion (multilingual, negation-aware)."""
from __future__ import annotations

import re

DELETION_REQUESTED, NOT_A_DELETION_REQUEST = "DELETION_REQUESTED", "NOT_A_DELETION_REQUEST"

# Phrases that explicitly withhold or narrow deletion. Checked first: they override any delete verb.
NEGATIONS = [
    r"not asking for deletion", r"do not (?:close|delete|remove)", r"don'?t (?:close|delete|remove)",
    r"keep the account", r"leave the account active", r"without removing", r"marketing lists? only",
    r"promotional emails?", r"unsubscribe", r"opt[- ]?out", r"i still (?:need|want)", r"not (?:to )?delete",
    r"not a request to (?:erase|delete|remove|close)", r"information request", r"leave (?:my|the) (?:profile|account)",
    r"continue using", r"still use it",
]
# Intent verbs / nouns for deletion in the languages present in the dataset.
DELETE_WORDS = [
    r"\bdelet\w*", r"\berase\w*", r"\bclos(?:e|ed|ing)\b", r"\bremov\w*", r"\bgone\b", r"account[- ]deletion",
    r"\bsuppression\b", r"\bsupprim\w*", r"\beffac\w*", r"\bélimin\w*", r"\belimin\w*", r"\bborr\w*",
    r"\bexclus[aã]o\b", r"\bexclu[ií]\w*", r"\bexcluir\b", r"\bapag\w*", r"\bcancell\w*", r"\bverwijder\w*",
    r"\bl[oö]sch\w*", r"\bentfern\w*", r"삭제", r"탈퇴", r"削除", r"退会", r"删除", r"刪除", r"注销",
]
NEG_RE = re.compile("|".join(NEGATIONS), re.IGNORECASE)
DEL_RE = re.compile("|".join(DELETE_WORDS), re.IGNORECASE)


def classify_request(text: str) -> str:
    t = (text or "").strip()
    if NEG_RE.search(t):
        return NOT_A_DELETION_REQUEST
    if DEL_RE.search(t):
        return DELETION_REQUESTED
    return NOT_A_DELETION_REQUEST
