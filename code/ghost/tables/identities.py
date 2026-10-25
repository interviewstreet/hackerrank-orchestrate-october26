"""Table 1: every identifier a person ever held -> user_id."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import AUDIT_LOG_CSV, IDENTITIES_CSV
from ..dataset_io import read_csv
from ..errors import DatasetError
from ..identifiers import email_hash, normalise

log = logging.getLogger(__name__)

_FIELD_KIND = {"email": "email", "email_hash": "hash", "phone": "phone"}


@dataclass(frozen=True)
class IdentityRow:
    identifier: str
    user_id: str
    kind: str        # email | hash | phone | user_id
    current: bool
    audit_id: str | None


def build_identity_rows() -> list[IdentityRow]:
    users = read_csv(IDENTITIES_CSV, ("user_id", "email", "phone", "email_hash"))
    audit = read_csv(AUDIT_LOG_CSV, ("audit_id", "user_id", "field_name", "old_value", "new_value"))

    rows: list[IdentityRow] = []
    for u in users:
        uid = u["user_id"]
        rows.append(IdentityRow(uid, uid, "user_id", True, None))
        rows.append(IdentityRow(normalise("email", u["email"]), uid, "email", True, None))
        rows.append(IdentityRow(normalise("hash", u["email_hash"]), uid, "hash", True, None))
        if u["phone"].strip():
            rows.append(IdentityRow(normalise("phone", u["phone"]), uid, "phone", True, None))

    for a in audit:
        kind = _FIELD_KIND.get(a["field_name"])
        if kind is None:
            log.warning("%s: unknown field_name %r ignored", a["audit_id"], a["field_name"])
            continue
        for value in (a["old_value"], a["new_value"]):
            if not value.strip():
                continue
            rows.append(IdentityRow(normalise(kind, value), a["user_id"], kind, False, a["audit_id"]))
            if kind == "email":  # hashes of historical emails are not always logged; derive them
                rows.append(IdentityRow(email_hash(value), a["user_id"], "hash", False, a["audit_id"]))

    return _dedupe(rows)


def _dedupe(rows: list[IdentityRow]) -> list[IdentityRow]:
    """One row per identifier. Prefer current over historical. Two users on one identifier is fatal."""
    best: dict[str, IdentityRow] = {}
    for r in rows:
        prev = best.get(r.identifier)
        if prev is None:
            best[r.identifier] = r
        elif prev.user_id != r.user_id:
            raise DatasetError(f"identifier {r.identifier!r} maps to {prev.user_id} and {r.user_id}")
        elif r.current and not prev.current:
            best[r.identifier] = r
    out = sorted(best.values(), key=lambda r: r.identifier)
    log.info("identities: %d identifiers for %d users", len(out), len({r.user_id for r in out}))
    return out
