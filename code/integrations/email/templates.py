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
        "We reviewed your data deletion request (reference {case_id}) and found that some of your personal data was still "
        "stored, or could reappear, in {findings_count} place(s). We have a plan of {remediation_count} step(s) to fix this "
        "and will run verification checks afterwards. We will confirm by email once those checks pass.\n\n"
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

INTERNAL_NOTE = "\n\n--- Internal audit note (for the reviewer; remove before approving if this goes to the customer) ---\n{explanation}\n"
REVIEW_NOTE = "\nFlagged for human review: {reason}\n"
