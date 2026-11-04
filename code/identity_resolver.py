"""
identity_resolver.py — Stage 1 of the deletion-audit pipeline.

Resolves a request email address to a stable user_id and assembles all
current and historical identifiers for the subject.

Design decisions
----------------
* Emails are always normalised to lowercase before any lookup.
* Email ownership is time-aware.  From user_identities.csv and the email
  changes in user_audit_log.csv we build, for each email, the periods each
  user owned it.  The request email resolves to the user who owned it at
  the request's requested_at (or audit_at, if requested_at is missing).
  With no time given, the current owner wins (the old behaviour).
* If several users could have owned the email at that time (e.g. two
  users with the same old email and unknown start dates), a warning is
  printed with the case_id and the user who gave the email up first is
  chosen: ownership is assumed to pass from one user to the next.
* Phone and email-hash history is also collected from the audit log.
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
from utils import parse_ts, to_utc, warn

_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


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

        # Maps user_id → identity row dict
        self._current_by_uid: dict[str, dict] = {}
        # Maps user_id → list of historical audit rows
        self._audit_by_uid: dict[str, list[dict]] = {}
        # Maps normalised email → ownership periods (start, end, user_id).
        # start is inclusive, end exclusive; None means open-ended.
        self._email_owners: dict[str, list[tuple[Optional[datetime], Optional[datetime], str]]] = {}

        self._load()
        self._build_email_owners()

    # ------------------------------------------------------------------
    # Private loading helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load both CSV files into memory."""
        # --- user_identities.csv ---
        with open(self._identities_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                self._current_by_uid[row["user_id"]] = row

        # --- user_audit_log.csv ---
        with open(self._audit_log_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                uid = row["user_id"]
                # Parse once. An empty event_time can't be placed in time, so
                # it is treated as before audit_at (kept, never rolled back):
                # searching one extra identifier is safer than missing one.
                row["_event_dt"] = parse_ts(
                    row.get("event_time"),
                    context=f"user_audit_log {row.get('audit_id', '?')} event_time"
                            " (treated as before audit_at)",
                )
                self._audit_by_uid.setdefault(uid, []).append(row)

    def _build_email_owners(self) -> None:
        """
        Turn each user's email changes into ownership periods.

        For a user whose email went  e0 --t1--> e1 --t2--> e2 (current):
            e0 owned (None, t1),  e1 owned [t1, t2),  e2 owned [t2, None)
        A user with no email change owns the snapshot email for all time.
        """
        def add(email: str, start, end, uid: str) -> None:
            email = email.lower().strip()
            if email:
                self._email_owners.setdefault(email, []).append((start, end, uid))

        for uid, ident in self._current_by_uid.items():
            changes = [a for a in self._audit_by_uid.get(uid, [])
                       if a["field_name"] == "email"]
            # Undated changes sort first (treated as the oldest)
            changes.sort(key=lambda a: (a["_event_dt"] or _MIN_DT, a["audit_id"]))
            start: Optional[datetime] = None
            for a in changes:
                t = a["_event_dt"]
                add(a["old_value"], start, t, uid)
                start = t
            if changes and changes[-1]["new_value"].strip().lower() != ident["email"].strip().lower():
                add(changes[-1]["new_value"], start, None, uid)   # inconsistent data: keep both
            add(ident["email"], start, None, uid)

    def _owner_at(self, email: str, at: Optional[datetime], case_id: str) -> Optional[str]:
        """
        Return the user_id that owned *email* at time *at*.
        at=None means "now", so the current owner wins.
        """
        periods = self._email_owners.get(email, [])
        if not periods:
            return None
        if len({uid for _, _, uid in periods}) == 1:
            return periods[0][2]                      # only one user ever had it

        def contains(p) -> bool:
            start, end, _ = p
            if at is None:
                return end is None
            return (start is None or start <= at) and (end is None or at < end)

        def end_key(p):                               # earliest end first; open end last
            return (p[1] is None, p[1] or _MIN_DT, p[2])

        where = f"{case_id}: " if case_id else ""
        when = at.isoformat() if at else "now"
        hits = sorted((p for p in periods if contains(p)), key=end_key)
        hit_users = sorted({p[2] for p in hits})
        if len(hit_users) == 1:
            return hit_users[0]
        if len(hit_users) > 1:
            chosen = hits[0][2]
            warn(f"{where}email {email!r} could belong to {', '.join(hit_users)} at {when}; "
                 f"chose {chosen} (gave the email up first, so owned it earliest)")
            return chosen

        # Nobody owned it at that time: take the most recent owner before it,
        # otherwise the first owner after it.
        before = [p for p in periods if p[1] is not None and at is not None and p[1] <= at]
        if before:
            chosen = max(before, key=lambda p: (p[1], p[2]))[2]
        else:
            chosen = min(periods, key=lambda p: (p[0] or _MIN_DT, p[2]))[2]
        warn(f"{where}email {email!r} had no owner at {when}; chose {chosen} "
             f"(nearest owner in time)")
        return chosen

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        request_email: str,
        audit_at: Optional[datetime] = None,
        requested_at: Optional[datetime] = None,
        case_id: str = "",
    ) -> Optional[IdentityBundle]:
        """
        Resolve *request_email* to a full IdentityBundle.

        Parameters
        ----------
        request_email:
            The email address supplied with the deletion request.
        audit_at:
            The audit cutoff timestamp (§6.2), e.g. from utils.parse_ts().
            A naive datetime is treated as UTC.  When provided, only audit
            log entries whose event_time is **at or before** this timestamp
            are included in the returned identifier bundle.
        requested_at:
            When the request was sent.  The email resolves to the user who
            owned it at this time.  Falls back to audit_at, then to "now".
        case_id:
            Only used to label warnings.

        Returns None if no user ever had this email.
        """
        norm = request_email.lower().strip()
        if audit_at is not None:
            audit_at = to_utc(audit_at)   # a naive datetime is taken as UTC
        if requested_at is not None:
            requested_at = to_utc(requested_at)

        def _after_audit(row: dict) -> bool:
            dt = row["_event_dt"]
            return audit_at is not None and dt is not None and dt > audit_at

        # Who owned the request email when the request was sent?
        lookup_at = requested_at if requested_at is not None else audit_at
        uid = self._owner_at(norm, lookup_at, case_id)
        identity_row = self._current_by_uid.get(uid) if uid else None
        if identity_row is None:
            return None
        audit_rows = self._audit_by_uid.get(uid, [])

        # The snapshot reflects the latest state, which may postdate audit_at.
        # Roll it back: undo every change after audit_at, newest first, so the
        # "current" fields are the values the subject actually had at audit_at
        # and no identifier that only appeared later leaks into the bundle.
        cur_email = identity_row["email"]
        cur_phone = identity_row["phone"]
        cur_hash = identity_row["email_hash"]
        if audit_at is not None:
            later = [a for a in audit_rows if _after_audit(a)]
            later.sort(key=lambda a: a["_event_dt"], reverse=True)
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
            if _after_audit(audit_row):
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
        history.sort(key=lambda c: (
            parse_ts(c.event_time, "history sort") if c.event_time.strip() else _MIN_DT,
            c.audit_id,
        ))

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

        Each dict must have 'email' and optionally 'audit_at', 'requested_at'
        (ISO-8601 str) and 'case_id'.
        Returns a list of (request_row, IdentityBundle | None) tuples.
        """
        results = []
        for req in requests:
            case_id = req.get("case_id", "")
            # Empty audit_at -> warning + None (no time filter)
            audit_at = parse_ts(req.get("audit_at"), context=f"{case_id or '?'} audit_at")
            requested_at = (
                parse_ts(req["requested_at"], context=f"{case_id or '?'} requested_at")
                if "requested_at" in req else None
            )
            results.append((req, self.resolve(req["email"], audit_at=audit_at,
                                              requested_at=requested_at,
                                              case_id=case_id)))
        return results
