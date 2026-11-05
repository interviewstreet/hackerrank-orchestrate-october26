"""Who may use the email actions. Identity comes from a secret token that only the server can check.

EMAIL_OPERATORS holds `name:sha256-of-token` pairs, comma separated, for example
    EMAIL_OPERATORS=Rachana:3f2a...64 hex chars...,Asha:9bd1...
Only the hash is stored, so a leaked .env does not leak a working login. The person sends the token itself in an
`Authorization: Bearer <token>` header; the server looks up the matching name and uses THAT name as the actor/approver
in the audit trail. A name sent in a request body is never trusted.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Dict, Mapping, Optional

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,59}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_TOKEN_LEN = 200


class OperatorConfigError(ValueError):
    """EMAIL_OPERATORS is malformed. The message never contains a hash or token."""


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


class Operators:
    def __init__(self, entries: Optional[Mapping[str, str]] = None):
        self._by_name: Dict[str, str] = {}
        for name, digest in (entries or {}).items():
            if not NAME_RE.match(name):
                raise OperatorConfigError("an operator name is invalid (letters, digits, space, . _ - ; up to 60 characters)")
            if not HASH_RE.match(digest):
                raise OperatorConfigError(f"the token hash for operator '{name}' must be 64 lowercase hex characters")
            if name.lower() in {n.lower() for n in self._by_name}:
                raise OperatorConfigError(f"operator '{name}' is listed twice")
            self._by_name[name] = digest

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Operators":
        return cls(parse_operators(env.get("EMAIL_OPERATORS", "")))

    @property
    def enabled(self) -> bool:
        return bool(self._by_name)

    def names(self):
        return sorted(self._by_name)

    def authenticate(self, token: str) -> Optional[str]:
        """Operator name for a valid token, else None. Compares against every entry so timing does not reveal which."""
        if not token or len(token) > MAX_TOKEN_LEN:
            return None
        digest = hash_token(token)
        found: Optional[str] = None
        for name, stored in self._by_name.items():
            if hmac.compare_digest(digest, stored):
                found = name
        return found


def parse_operators(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in (raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        name, sep, digest = item.rpartition(":")
        if not sep or not name.strip():
            raise OperatorConfigError("EMAIL_OPERATORS entries must look like name:sha256hash")
        out[name.strip()] = digest.strip().lower()
    return out


def upsert_operator_line(env_text: str, name: str, digest: str) -> str:
    """Return env_text with `name` added to (or replaced in) the EMAIL_OPERATORS line. Other lines are kept as they are."""
    if not NAME_RE.match(name) or not HASH_RE.match(digest):
        raise OperatorConfigError("invalid operator name or hash")
    nl = "\r\n" if "\r\n" in env_text else "\n"
    lines = env_text.split(nl) if env_text else []
    idx = next((i for i, ln in enumerate(lines) if ln.startswith("EMAIL_OPERATORS=")), None)
    current = parse_operators(lines[idx].split("=", 1)[1]) if idx is not None else {}
    current = {n: h for n, h in current.items() if n.lower() != name.lower()}
    current[name] = digest
    line = "EMAIL_OPERATORS=" + ",".join(f"{n}:{h}" for n, h in current.items())
    if idx is not None:
        lines[idx] = line
    else:
        if lines and lines[-1] == "":
            lines.pop()
        lines.append(line)
        lines.append("")
    return nl.join(lines)
