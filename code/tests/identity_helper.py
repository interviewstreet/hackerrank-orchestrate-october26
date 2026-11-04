"""Test-only identity resolution (the real one belongs to the identity module).

Builds SubjectIdentifiers from user_identities.csv + user_audit_log.csv so the
integration tests can query the scanner the way the auditor will.
"""

import csv
from functools import lru_cache
from pathlib import Path

from evidence import SubjectIdentifiers

FIELD_SETS = {"email": "emails", "phone": "phones", "email_hash": "email_hashes", "name": "names"}


@lru_cache(maxsize=None)
def _tables(dataset_dir: str):
    d = Path(dataset_dir)
    ids = {r["user_id"]: r for r in csv.DictReader((d / "user_identities.csv").open(encoding="utf-8"))}
    audit = list(csv.DictReader((d / "user_audit_log.csv").open(encoding="utf-8")))
    return ids, audit


def user_for_email(dataset_dir, email: str):
    ids, audit = _tables(str(dataset_dir))
    e = email.strip().lower()
    for u in ids.values():
        if u["email"].lower() == e:
            return u["user_id"]
    for a in audit:
        if a["field_name"] == "email" and e in (a["old_value"].lower(), a["new_value"].lower()):
            return a["user_id"]
    return None


def identifiers_for(dataset_dir, user_id: str, resource_ids=()) -> SubjectIdentifiers:
    ids, audit = _tables(str(dataset_dir))
    u = ids[user_id]
    vals = {"emails": {u["email"]}, "phones": {u["phone"]}, "email_hashes": {u["email_hash"]}, "names": {u["name"]}}
    for a in audit:
        if a["user_id"] == user_id and a["field_name"] in FIELD_SETS:
            vals[FIELD_SETS[a["field_name"]]].update({a["old_value"], a["new_value"]})
    return SubjectIdentifiers(user_id=user_id, resource_ids=frozenset(resource_ids),
                              **{k: frozenset(v) for k, v in vals.items()})


def identifiers_for_email(dataset_dir, email: str, resource_ids=()) -> SubjectIdentifiers:
    uid = user_for_email(dataset_dir, email)
    assert uid, f"no identity for {email}"
    return identifiers_for(dataset_dir, uid, resource_ids)
