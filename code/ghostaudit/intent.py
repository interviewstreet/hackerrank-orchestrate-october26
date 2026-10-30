"""Request intent: does the request text authorize deletion? LLM (batched, cached) + offline heuristic."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass

from .config import PROMPTS_DIR

log = logging.getLogger(__name__)

DELETE = "DELETE"
NON_DELETE = "NON_DELETE"
BATCH_SIZE = 25

# Explicit statements that the account must stay or that this is not an erasure request.
NEGATION_PATTERNS = [
    r"\bnot (?:asking|a request|requesting)\b[^.]*\b(?:delet|eras|remov|clos)",
    r"\b(?:do not|don't|dont|please don't|without)\s+(?:\w+\s+){0,2}(?:clos|delet|remov|eras|chang)",
    r"\b(?:keep|leave) (?:the|my) (?:account|profile)",
    r"\bleave the account active\b|\bcontinue using\b|\bstill (?:want|need|use)\b",
    r"\b(?:thinking|considering) (?:about )?(?:delet|clos|remov)\w*\b[^.]*[.?]\s*what would happen\b",
    r"\bmarketing (?:\w+ )?only\b|\bonly\b[^.]*\bmarketing\b",
    r"no (?:quiero|deseo) (?:eliminar|borrar)|ne (?:pas|veux pas) (?:supprimer|fermer)",
    r"삭제하지\s*마|削除しないで|não (?:quero )?(?:excluir|apagar)",
    r"\bне (?:нужно |надо |стоит )?(?:удаля|удали|стира|закрыва)|\bnie (?:usuwa|kasuj|zamyka)|\bnicht (?:lösch|entfern)",
    r"请不要删除|不要删除|لا تحذف|मत हटा",
]
# Topics that are not deletion on their own.
NON_DELETE_TOPICS = [
    r"\bpromotional emails?\b|\bunsubscribe\b|\bnewsletter\b",
    r"\bdownload\b|\bportable format\b|\bcopy of (?:the|my|last)\b|\bexport (?:my|of my)\b",
    r"\binvoices?\b|\breceipts?\b",
    r"\bwhat (?:personal )?(?:information|data) you hold\b|\baccess request\b|\binformation request\b",
    r"\breset(?:ting)? (?:the |my )?(?:login|password)\b|\bcan't access\b|\bcannot access\b",
    r"\bmisspelled\b|\bcorrect (?:it|my)\b|\bchange the email\b|\breplace it with\b|\bout of date\b",
]
DELETION_PATTERNS = [
    r"\bdelet\w*|\beras\w*|\bremov\w*|\bclos(?:e|ing|ure)\b|\bpurge\b|\bwipe\b|\bforget me\b|right to be forgotten",
    r"\b(?:profile|account|data) is gone\b|\bcannot identify me\b|\bcan't identify me\b|\bno longer identif",
    r"\bget rid of (?:my|the)\b|\bnothing\b[^.]*\bcan identify me\b",
    r"\bsuppression\b",
    r"\belimin\w*|\bborr[aeoá]\w*|\bsuprim\w*|\bcerrar\b",          # es
    r"\bsupprim\w*|\beffac\w*|\bfermer\b|\bfermeture\b",          # fr
    r"\bexclu\w*|\bapag\w*|\bencerr\w*",                           # pt
    r"\blösch\w*|\bentfern\w*|\bschließ\w*|\bkündig\w*",           # de
    r"削除|退会|消去|抹消",                                         # ja
    r"삭제|탈퇴|폐쇄",                                              # ko
    r"\bудал\w*|\bстер\w*|\bсотр\w*|\bзакры\w*",                 # ru
    r"\bвидал\w*|\bвилуч\w*",                                     # uk
    r"\busu[nń]\w*|\bskasuj\w*|\bzamkni\w*",                      # pl
    r"\bcancell\w*|\bchiud\w*",                                   # it
    r"\bverwijder\w*|\bopheffen\b",                               # nl
    r"\bsil(?:in|iniz|mek|menizi)\b|\bkapat\w*",                   # tr
    r"删除|刪除|注销|註銷|清除",                                    # zh
    r"حذف|احذف|امسح|مسح",                                         # ar
    r"हटा|मिटा",                                                   # hi
]


@dataclass(frozen=True)
class IntentLabel:
    label: str
    confidence: float
    source: str
    reason: str = ""


def heuristic(text: str) -> IntentLabel:
    t = " ".join((text or "").lower().split())
    for p in NEGATION_PATTERNS:
        if re.search(p, t):
            return IntentLabel(NON_DELETE, 0.9, "heuristic", f"negation:{p[:30]}")
    deletion = any(re.search(p, t) for p in DELETION_PATTERNS)
    if deletion:
        return IntentLabel(DELETE, 0.9, "heuristic", "deletion verb")
    for p in NON_DELETE_TOPICS:
        if re.search(p, t):
            return IntentLabel(NON_DELETE, 0.85, "heuristic", f"topic:{p[:30]}")
    return IntentLabel(NON_DELETE, 0.6, "heuristic", "no deletion authorization found")


def _text_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class IntentClassifier:
    def __init__(self, llm=None):
        self.llm = llm
        self.labels: dict[str, IntentLabel] = {}
        self.heuristic_labels: dict[str, IntentLabel] = {}

    def classify_all(self, texts: list[str]) -> dict[str, IntentLabel]:
        unique = sorted(set(texts))
        for t in unique:
            self.heuristic_labels[t] = heuristic(t)
        llm_labels: dict[str, IntentLabel] = {}
        if self.llm is not None:
            template = (PROMPTS_DIR / "intent.md").read_text(encoding="utf-8")
            for i in range(0, len(unique), BATCH_SIZE):
                batch = unique[i:i + BATCH_SIZE]
                payload = json.dumps([{"id": _text_id(t), "text": t} for t in batch], ensure_ascii=False, indent=0)
                res = self.llm.complete(task="intent", prompt=template.replace("{{requests}}", payload),
                                        json_schema={"type": "object"})
                parsed = res.parsed_json if res else None
                by_id = {}
                if isinstance(parsed, dict):
                    for item in parsed.get("labels", []):
                        if isinstance(item, dict) and item.get("label") in (DELETE, NON_DELETE):
                            by_id[str(item.get("id"))] = item
                for t in batch:
                    item = by_id.get(_text_id(t))
                    if item:
                        llm_labels[t] = IntentLabel(item["label"], float(item.get("confidence") or 0.8),
                                                    "llm", str(item.get("reason") or ""))
        for t in unique:
            self.labels[t] = llm_labels.get(t) or self.heuristic_labels[t]
        return self.labels

    def disagreements(self) -> list[tuple[str, IntentLabel, IntentLabel]]:
        return [(t, self.labels[t], self.heuristic_labels[t]) for t in sorted(self.labels)
                if self.labels[t].source == "llm" and self.labels[t].label != self.heuristic_labels[t].label]
