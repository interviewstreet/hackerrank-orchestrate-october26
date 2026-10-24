"""Read-only investigator tools over participant evidence (plan 7.4, D19).

* ``search_evidence(query)``: exact-id grep first, then BM25 over line documents.
* ``read_evidence(id)``: parsed rows (vision rows for PNG) and the raw text of one file or activity row.
* ``query_facts(resource_id | identifier)``: fact-store rows for a resource or an identifier.

Every tool takes the case cutoff: files with ``captured_at > audit_at`` and later activity rows do
not exist for the agent. No tool writes anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from rank_bm25 import BM25Okapi

import safety
from evidence.common import Identifiers
from facts import FactStore
from loaders import Dataset, normalize_email

MAX_HITS = 8
MAX_ROWS = 30
LINE_CHARS = 240
TOKEN = re.compile(r"[a-z0-9_@.+-]+")


@dataclass(frozen=True)
class Doc:
    evidence_id: str
    line_no: int
    text: str
    available_at: datetime


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def _safe(text: str) -> str:
    """Untrusted evidence text for the model: a line with an injection pattern is withheld (D20)."""
    return "\n".join("[line withheld: injection pattern]" if safety.screen(line) else line
                     for line in text.splitlines())


class Corpus:
    """Raw text of every evidence file (OCR / PDF text for images and documents) and activity row."""

    def __init__(self, data: Dataset, store: FactStore, raw_text: dict[str, str]):
        self.store = store
        self.available: dict[str, datetime] = {}
        self.text: dict[str, str] = {}
        docs: list[Doc] = []
        for ev in data.evidence_files:
            text = raw_text.get(ev.file_id, "")
            self.text[ev.file_id], self.available[ev.file_id] = text, ev.captured_at
            for n, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    docs.append(Doc(ev.file_id, n, line.strip()[:LINE_CHARS], ev.captured_at))
        for a in data.activity:
            line = (f"{a.activity_id} {a.event_time.isoformat()} {a.event_type} {a.source_system} -> "
                    f"{a.target_system} {a.resource_id} {a.reported_result} {a.details}")
            self.text[a.activity_id], self.available[a.activity_id] = line, a.event_time
            docs.append(Doc(a.activity_id, 1, line[:LINE_CHARS], a.event_time))
        self.docs = docs
        self.bm25 = BM25Okapi([_tokens(d.text) for d in docs])

    def visible(self, evidence_id: str, cutoff: datetime) -> bool:
        return evidence_id in self.available and self.available[evidence_id] <= cutoff

    # ------------------------------------------------------------ tools

    def search_evidence(self, query: str, cutoff: datetime) -> list[dict]:
        query = query.strip()
        hits: list[Doc] = []
        if re.fullmatch(r"[\w.@+-]+", query):          # exact id / identifier grep first
            needle = query.lower()
            hits = [d for d in self.docs if d.available_at <= cutoff and needle in d.text.lower()]
        if len(hits) < MAX_HITS:
            scores = self.bm25.get_scores(_tokens(query))
            ranked = sorted(range(len(self.docs)), key=lambda i: (-scores[i], i))
            seen = set(hits)
            for i in ranked:
                if scores[i] <= 0 or len(hits) >= MAX_HITS:
                    break
                d = self.docs[i]
                if d.available_at <= cutoff and d not in seen:
                    hits.append(d)
        return [{"evidence_id": d.evidence_id, "line": d.line_no, "text": _safe(d.text)} for d in hits[:MAX_HITS]]

    def read_evidence(self, evidence_id: str, cutoff: datetime) -> dict:
        if not self.visible(evidence_id, cutoff):
            return {"error": f"{evidence_id} does not exist at the audit time"}
        rows = [self._row(o) for o in sorted(self.store.observations.values(), key=lambda o: o.obs_id)
                if o.file_id == evidence_id and self.store.admissible(o, cutoff)][:MAX_ROWS]
        text = self.text.get(evidence_id, "")
        return {"evidence_id": evidence_id, "parsed_rows": rows, "raw_text": _safe(text[:6000])}

    def query_facts(self, query: str, cutoff: datetime) -> list[dict]:
        query = query.strip()
        obs = self.store.for_resource(query, cutoff)
        if not obs:
            keys = Identifiers()
            if "@" in query:
                keys.emails.add(normalize_email(query))
            elif query.startswith("user_"):
                keys.user_ids.add(query)
            else:
                keys.hashes.add(query.lower())
            obs = self.store.linked(keys, cutoff)
        return [self._row(o) for o in obs[:MAX_ROWS]]

    @staticmethod
    def _row(o) -> dict:
        state = {k: getattr(o, k) for k in ("exists", "treatment", "flow_state", "restore_state") if getattr(o, k)}
        return {"evidence_id": o.file_id, "system_id": o.system_id, "resource_id": o.resource_id,
                "copy": o.physical_copy, "assertion": o.assertion, "observed_at": o.state_observed_at.isoformat(),
                "state": state, "identifiers": o.link_ids.as_dict()}
