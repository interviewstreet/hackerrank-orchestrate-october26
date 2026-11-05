"""Email wording. Requester-facing text never contains internal resource or evidence ids."""
from __future__ import annotations

from typing import Dict

SUBJECTS: Dict[str, str] = {
    "COMPLETE": "Your data deletion request is complete (ref {case_id})",
    "INCOMPLETE": "Update on your data deletion request (ref {case_id})",
    "NOT_APPLICABLE": "About your recent request (ref {case_id})",
}

BODIES: Dict[str, str] = {
    "COMPLETE": (
        "Hello,\n\n"
        "We have finished checking your data deletion request (reference {case_id}). "
        "Across {systems_checked} systems, the checks we ran confirm that your personal data has been removed or is held "
        "only in the form our retention policy requires.\n\n"
        "If you have questions, just reply to this email and quote the reference above.\n\n"
        "Regards,\nThe Privacy Team"
    ),
    "INCOMPLETE": (
        "Hello,\n\n"
        "Thank you for your data deletion request (reference {case_id}). Your request is being processed and the deletion "
        "is still in progress. When we reviewed it, we found that some of your personal data was still stored, or could "
        "reappear, in {findings_count} place(s).\n\n"
        "{systems_clause}"
        "We have a plan of {remediation_count} step(s) to complete the deletion and will run verification checks "
        "afterwards. We will confirm by email only once those checks have passed successfully; until then, please do not "
        "treat the deletion as complete. We are not able to promise a completion date.\n\n"
        "Some records may be kept where the law or our retention policy requires it, for example a minimal account "
        "reference that no longer contains your name, email address or phone number.\n\n"
        "If you have questions, just reply to this email and quote the reference above.\n\n"
        "Regards,\nThe Privacy Team"
    ),
    "NOT_APPLICABLE": (
        "Hello,\n\n"
        "Thank you for your message (reference {case_id}). It was not a request to delete your data, so we did not start "
        "a deletion audit. If you do want your data deleted, please reply and say so clearly.\n\n"
        "Regards,\nThe Privacy Team"
    ),
}

# Customer-safe wording for the kinds of system a case actually touches. Matched on the system id's name only; the
# id itself is never shown. Order here is the order the phrases appear in the email.
SYSTEM_PHRASES = (
    (("account", "identity", "database", "db"), "account and identity databases"),
    (("log",), "application logs"),
    (("search", "cache"), "search indexes and caches"),
    (("analytics",), "analytics records"),
    (("support",), "support records and attachments"),
    (("export", "storage", "marketing"), "exports, stored files and marketing records"),
    (("integration", "sync", "connector"), "connected services that copy data between systems"),
    (("backup", "archive"), "backup and retention systems"),
)

SYSTEMS_CLAUSE = ("The deletion covers the following kinds of system where our review found your data: {systems}.\n\n")

INTERNAL_NOTE ="\n\n--- Internal audit note (for the reviewer; remove before approving if this goes to the customer) ---\n{explanation}\n"
REVIEW_NOTE = "\nFlagged for human review: {reason}\n"
