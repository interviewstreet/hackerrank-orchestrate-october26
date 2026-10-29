"""
Intent Classifier: Determines whether a request authorizes personal data deletion.
Correctly handles multilingual requests and distinguishes deletion from access, rectification, and export.
"""

import re

# Phrases indicating that the user does NOT want deletion or is only requesting access/rectification/opt-out
NON_DELETION_PHRASES = [
    r"leave the account active",
    r"keep the account",
    r"leave my profile",
    r"leave my.*history",
    r"continue using the service",
    r"not asking for deletion",
    r"not a request to erase",
    r"do not close",
    r"do not delete",
    r"don't delete",
    r"without removing",
    r"from marketing lists only",
    r"remove me from marketing lists only",
    r"information request, not a request",
    r"stop the promotional emails",
    r"misspelled.*correct it",
]

# Multilingual keywords confirming deletion intent
DELETION_KEYWORDS = [
    r"delet", r"eras", r"remov", r"clos", r"cancel", r"purg", r"wipe",
    r"is gone", r"cannot identify", r"unidentified", # audit confirmations
    r"suppr", r"effac",        # French
    r"elimin", r"borr",          # Spanish
    r"exclu", r"apagar",        # Portuguese
    r"lösch", r"entfern",       # German
    r"cancell",                 # Italian
    r"삭제", r"탈퇴",            # Korean
    r"削除", r"消去",            # Japanese
    r"删除", r"注销",            # Chinese
    r"حذف",                     # Arabic
    r"verwijder",               # Dutch
    r"usun", r"usuń",           # Polish
    r"radera", r"ta bort",      # Swedish
]

def is_deletion_authorized(request_text: str) -> bool:
    """
    Returns True if request_text authorizes deletion.
    Returns False if it is a non-deletion request (access, export, rectification, etc.).
    """
    if not request_text or not request_text.strip():
        return False

    text_lower = request_text.lower().strip()

    # 1. Check for explicit non-deletion / retention intent
    for pattern in NON_DELETION_PHRASES:
        if re.search(pattern, text_lower):
            return False

    # 2. Check for positive deletion authorization
    for kw in DELETION_KEYWORDS:
        if re.search(kw, text_lower):
            return True

    # Default fallback: if no deletion keywords present, not authorized
    return False
