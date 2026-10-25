"""Identity resolution: current + historical identifiers.

A request email may be the user's current email (418/518 cases) or an older
email that only survives in user_audit_log.csv (100/518). We therefore index
current identities and *every* old/new value in the audit log.

Historical-value policy: an audit event's ``old_value`` was true in the past,
so it is always safe to search for it. A ``new_value`` dated after a case's
``audit_at`` only means the value came into use later; including it cannot
create a finding by itself because every fact used for a case is still
filtered to ``observed_at <= audit_at``. We document that here rather than
adding unstable per-case cutoffs.
"""
import hashlib
import re


def norm_email(value):
    return str(value).strip().lower() if value else ""


def email_hash(email):
    return hashlib.sha256(norm_email(email).encode("utf-8")).hexdigest()


def norm_phone(value):
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


class IdentityResolver:
    def __init__(self, identities, audit_log):
        self.identities = identities
        self.audit_log = audit_log
        self.by_user = {}
        self.by_email = {}
        self.by_hash = {}
        self.by_phone = {}
        for row in identities:
            uid = row["user_id"]
            self.by_user[uid] = {
                "user_id": uid, "name": row.get("name", ""),
                "emails": set(), "hashes": set(), "phones": set(),
            }
            self._add_email(uid, row.get("email"))
            if row.get("email_hash"):
                self.by_user[uid]["hashes"].add(row["email_hash"].strip().lower())
                self.by_hash[row["email_hash"].strip().lower()] = uid
            self._add_phone(uid, row.get("phone"))
        for ev in audit_log:
            uid = ev["user_id"]
            if uid not in self.by_user:
                self.by_user[uid] = {"user_id": uid, "name": "",
                                     "emails": set(), "hashes": set(), "phones": set()}
            field = ev["field_name"]
            for raw in (ev.get("old_value"), ev.get("new_value")):
                if not raw:
                    continue
                if field == "email":
                    self._add_email(uid, raw)
                elif field == "email_hash":
                    h = raw.strip().lower()
                    self.by_user[uid]["hashes"].add(h)
                    self.by_hash[h] = uid
                elif field == "phone":
                    self._add_phone(uid, raw)
        # Every known email also contributes its sha256 hash.
        for uid, data in self.by_user.items():
            for e in list(data["emails"]):
                h = email_hash(e)
                data["hashes"].add(h)
                self.by_hash.setdefault(h, uid)

    def _add_email(self, uid, raw):
        e = norm_email(raw)
        if e and "@" in e:
            self.by_user[uid]["emails"].add(e)
            self.by_email[e] = uid

    def _add_phone(self, uid, raw):
        p = norm_phone(raw)
        if len(p) >= 7:
            self.by_user[uid]["phones"].add(p)
            self.by_phone[p] = uid

    def resolve(self, email):
        """Return user_id for a request email (current or historical)."""
        e = norm_email(email)
        if e in self.by_email:
            return self.by_email[e]
        h = email_hash(e)
        return self.by_hash.get(h)

    def identifiers(self, user_id):
        """All identifiers for a user; name is a secondary hint only."""
        data = self.by_user.get(user_id)
        if not data:
            return {"emails": set(), "hashes": set(), "phones": set(),
                    "user_ids": set(), "name": ""}
        return {
            "emails": set(data["emails"]),
            "hashes": set(data["hashes"]),
            "phones": set(data["phones"]),
            "user_ids": {user_id},
            "name": data["name"],
        }
