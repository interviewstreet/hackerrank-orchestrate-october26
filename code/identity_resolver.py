"""
identity_resolver.py — Stage 1 of the deletion-audit pipeline.

Resolves a request email address to a stable user_id and assembles all
current and historical identifiers for the subject.

Design decisions
----------------
* Emails are always normalised to lowercase before any lookup.
* The resolution chain is:
    1. Current identity snapshot (user_identities.csv)
    2. Historical email addresses (user_audit_log.csv, field_name='email')
* Phone and email-hash history is also collected from the audit log.
* An email cannot belong to two different users simultaneously in this
  dataset (verified by data analysis — no such case exists).
* If resolution fails, returns None; callers must handle the missing case.
* audit_at: when supplied, only audit entries at or before that timestamp
  are included in the returned identifier bundle (§6.2 contract).  The
  email-lookup tables always use the full history to identify the user;
  only the returned identifiers are time-filtered.  The snapshot's
  email/phone/email_hash are rolled back through any audit changes after
  audit_at, so an identifier that only became current later is excluded.
* email_hash is SHA-256(lowercase_email) — verified against all 850 rows.
  We compute the hash for each historical email so the bundle's
  all_email_hashes() covers every address the subject ever used.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models import IdentityBundle, IdentityChange


def _parse_dt(ts: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp (with or without Z suffix)."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _sha256(email: str) -> str:
    """Return the SHA-256 hex digest of the lower-cased email."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


class IdentityResolver:
    """
    Loads identity data once at construction time; resolve() is then O(1).

    Parameters
    ----------
    identities_path : Path-like
        Path to user_identities.csv
    audit_log_path : Path-like
        Path to user_audit_log.csv
    """

    def __init__(self, identities_path: str | Path, audit_log_path: str | Path):
        self._identities_path = Path(identities_path)
        self._audit_log_path = Path(audit_log_path)

        # Maps normalised email → identity row dict
        self._current_by_email: dict[str, dict] = {}
        # Maps user_id → identity row dict
        self._current_by_uid: dict[str, dict] = {}
        # Maps normalised old_email → user_id  (email history)
        self._historical_email_to_uid: dict[str, str] = {}
        # Maps user_id → list of historical audit rows
        self._audit_by_uid: dict[str, list[dict]] = {}

        self._load()

    # ------------------------------------------------------------------
    # Private loading helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load both CSV files into memory."""
        # --- user_identities.csv ---
        with open(self._identities_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                norm = row["email"].lower().strip()
                self._current_by_email[norm] = row
                self._current_by_uid[row["user_id"]] = row

        # --- user_audit_log.csv ---
        with open(self._audit_log_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                uid = row["user_id"]
                self._audit_by_uid.setdefault(uid, []).append(row)
                if row["field_name"] == "email":
                    old_norm = row["old_value"].lower().strip()
                    # Only register if no current user owns this email
                    # (prevents shadowing a live account)
                    if old_norm not in self._current_by_email:
                        self._historical_email_to_uid[old_norm] = uid

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        request_email: str,
        audit_at: Optional[datetime] = None,
    ) -> Optional[IdentityBundle]:
        """
        Resolve *request_email* to a full IdentityBundle.

        Parameters
        ----------
        request_email:
            The email address supplied with the deletion request.
        audit_at:
            The audit cutoff timestamp (§6.2).  When provided, only audit
            log entries whose event_time is **at or before** this timestamp
            are included in the returned identifier bundle.  The user-lookup
            tables always use the full history to identify the user.

        Returns None if no match is found in either the current snapshot
        or the historical audit log.
        """
        norm = request_email.lower().strip()

        # Step 1 — try current snapshot
        identity_row = self._current_by_email.get(norm)

        # Step 2 — try historical emails (full history, no time filter)
        if identity_row is None:
            uid = self._historical_email_to_uid.get(norm)
            if uid is not None:
                identity_row = self._current_by_uid.get(uid)

        if identity_row is None:
            return None

        uid = identity_row["user_id"]
        audit_rows = self._audit_by_uid.get(uid, [])

        # The snapshot reflects the latest state, which may postdate audit_at.
        # Roll it back: undo every change after audit_at, newest first, so the
        # "current" fields are the values the subject actually had at audit_at
        # and no identifier that only appeared later leaks into the bundle.
        cur_email = identity_row["email"]
        cur_phone = identity_row["phone"]
        cur_hash = identity_row["email_hash"]
        if audit_at is not None:
            later = [a for a in audit_rows if _parse_dt(a["event_time"]) > audit_at]
            later.sort(key=lambda a: _parse_dt(a["event_time"]), reverse=True)
            email_rolled = hash_rolled = False
            for a in later:
                old_val = a["old_value"].strip()
                if not old_val:
                    continue
                if a["field_name"] == "email":
                    cur_email, email_rolled = old_val, True
                elif a["field_name"] == "phone":
                    cur_phone = old_val
                elif a["field_name"] == "email_hash":
                    cur_hash, hash_rolled = old_val, True
            if email_rolled and not hash_rolled:
                cur_hash = _sha256(cur_email)

        # Collect history for this user, respecting audit_at cutoff
        hist_emails: list[str] = []
        hist_phones: list[str] = []
        # We collect hashes from stored audit entries …
        hist_hashes_stored: list[str] = []
        history: list[IdentityChange] = []

        for audit_row in audit_rows:
            # Time-filter: skip entries that occur after audit_at
            if audit_at is not None:
                entry_time = _parse_dt(audit_row["event_time"])
                if entry_time > audit_at:
                    continue

            history.append(IdentityChange(
                audit_id=audit_row["audit_id"],
                field_name=audit_row["field_name"],
                old_value=audit_row["old_value"],
                new_value=audit_row["new_value"],
                event_time=audit_row["event_time"],
            ))

            field = audit_row["field_name"]
            old_val = audit_row["old_value"].strip()
            if not old_val:
                continue

            if field == "email":
                low = old_val.lower()
                if low not in hist_emails:
                    hist_emails.append(low)
            elif field == "phone":
                if old_val not in hist_phones:
                    hist_phones.append(old_val)
            elif field == "email_hash":
                if old_val not in hist_hashes_stored:
                    hist_hashes_stored.append(old_val)

        # … and also compute SHA-256 for every historical email so the
        # bundle's all_email_hashes() covers every address the subject used.
        hist_hashes_computed = [
            _sha256(e) for e in hist_emails
            if _sha256(e) not in hist_hashes_stored
        ]
        hist_hashes = hist_hashes_stored + hist_hashes_computed
        history.sort(key=lambda c: (_parse_dt(c.event_time), c.audit_id))

        return IdentityBundle(
            user_id=uid,
            current_email=cur_email,
            current_name=identity_row["name"],
            current_phone=cur_phone,
            current_email_hash=cur_hash,
            historical_emails=hist_emails,
            historical_phones=hist_phones,
            historical_email_hashes=hist_hashes,
            request_email=request_email,
            history=history,
        )

    def resolve_all(
        self, requests: list[dict]
    ) -> list[tuple[dict, Optional[IdentityBundle]]]:
        """
        Resolve a list of request dicts.

        Each dict must have 'email' and optionally 'audit_at' (ISO-8601 str).
        Returns a list of (request_row, IdentityBundle | None) tuples.
        """
        results = []
        for req in requests:
            audit_at: Optional[datetime] = None
            if req.get("audit_at"):
                audit_at = _parse_dt(req["audit_at"])
            results.append((req, self.resolve(req["email"], audit_at=audit_at)))
        return results
