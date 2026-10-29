"""
Identity Resolver: Resolves current and historical user identifiers.
Merges user_identities.csv and user_audit_log.csv into consolidated identity entities.
"""

import csv
from pathlib import Path
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field

@dataclass
class UserIdentity:
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: str
    historical_emails: Set[str] = field(default_factory=set)
    historical_phones: Set[str] = field(default_factory=set)
    historical_names: Set[str] = field(default_factory=set)
    all_identifiers: Set[str] = field(default_factory=set)

    def compile_identifiers(self):
        self.all_identifiers = {
            self.user_id,
            self.email,
            self.name,
            self.phone,
            self.email_hash,
        }
        self.all_identifiers.update(self.historical_emails)
        self.all_identifiers.update(self.historical_phones)
        self.all_identifiers.update(self.historical_names)
        self.all_identifiers.discard("")
        self.all_identifiers.discard(None)

class IdentityResolver:
    def __init__(self, dataset_dir: Path):
        self.dataset_dir = Path(dataset_dir)
        self.users: Dict[str, UserIdentity] = {}
        self.email_to_uid: Dict[str, str] = {}
        self.phone_to_uid: Dict[str, str] = {}
        self.hash_to_uid: Dict[str, str] = {}
        self._load()

    def _load(self):
        # 1. Load current identities
        identities_file = self.dataset_dir / "user_identities.csv"
        if identities_file.exists():
            with open(identities_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = row["user_id"]
                    identity = UserIdentity(
                        user_id=uid,
                        name=row.get("name", "").strip(),
                        email=row.get("email", "").strip().lower(),
                        phone=row.get("phone", "").strip(),
                        email_hash=row.get("email_hash", "").strip().lower(),
                        updated_at=row.get("updated_at", "").strip(),
                    )
                    self.users[uid] = identity
                    if identity.email:
                        self.email_to_uid[identity.email] = uid
                    if identity.phone:
                        self.phone_to_uid[identity.phone] = uid
                    if identity.email_hash:
                        self.hash_to_uid[identity.email_hash] = uid

        # 2. Load historical audit logs
        audit_file = self.dataset_dir / "user_audit_log.csv"
        if audit_file.exists():
            with open(audit_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = row["user_id"]
                    if uid not in self.users:
                        # Placeholder if user not in snapshot
                        self.users[uid] = UserIdentity(
                            user_id=uid,
                            name="", 
                            email="", 
                            phone="", 
                            email_hash="", 
                            updated_at=""
                        )
                    user = self.users[uid]
                    field_name = row.get("field_name", "").strip()
                    old_val = row.get("old_value", "").strip()
                    new_val = row.get("new_value", "").strip()

                    if field_name == "email":
                        if old_val:
                            user.historical_emails.add(old_val.lower())
                            self.email_to_uid[old_val.lower()] = uid
                        if new_val:
                            user.historical_emails.add(new_val.lower())
                            self.email_to_uid[new_val.lower()] = uid
                    elif field_name == "phone":
                        if old_val:
                            user.historical_phones.add(old_val)
                            self.phone_to_uid[old_val] = uid
                        if new_val:
                            user.historical_phones.add(new_val)
                            self.phone_to_uid[new_val] = uid
                    elif field_name == "name":
                        if old_val:
                            user.historical_names.add(old_val)
                        if new_val:
                            user.historical_names.add(new_val)

        # 3. Compile all identifiers
        for user in self.users.values():
            user.compile_identifiers()

    def resolve(self, identifier: str) -> Optional[UserIdentity]:
        ident = identifier.strip().lower()
        # Try direct email
        if ident in self.email_to_uid:
            return self.users.get(self.email_to_uid[ident])
        # Try direct user_id
        if identifier.strip() in self.users:
            return self.users.get(identifier.strip())
        # Try phone
        if identifier.strip() in self.phone_to_uid:
            return self.users.get(self.phone_to_uid[identifier.strip()])
        # Try hash
        if ident in self.hash_to_uid:
            return self.users.get(self.hash_to_uid[ident])
        return None
