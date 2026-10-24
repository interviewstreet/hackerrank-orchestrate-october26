"""Clause-level deletion-intent rules.

The text is split into sentences, then clauses (commas, semicolons, "but", "so", ...).
Each clause produces signals:

* ``delete``    - a request to delete/erase/remove/close (base form, noun, or a request
                  frame such as "would like it deleted"). Past-tense reports ("I deleted
                  my account") are context only.
* ``verify``    - a request to check or confirm that a deletion happened
                  ("verify that my account was deleted", "audit the deletion").
* ``negated``   - a deletion term under a negator in the same clause
                  ("not asking for deletion", "don't delete", "without removing").
* ``keep``      - the person wants to keep the account ("leave the account active").
* ``marketing`` - removal limited to marketing ("remove me from marketing lists only").
* ``other``     - a different request (update, correct, download, copy, access, ...).
* ``deleted_context`` / ``remnant`` - a past deletion ("had been deleted") and data
                  that survived it ("I can still find traces"). Together they mean DELETE.

Classes: DELETE, VERIFY_DELETE (counts as deletion), NOT_DELETION, AMBIGUOUS.
Positive and negative signals together, or no signal at all, give AMBIGUOUS.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from schema import DELETION_INTENTS, IntentLabel

# Plain-string labels; the values come from schema.IntentLabel.
DELETE = IntentLabel.DELETE.value
VERIFY_DELETE = IntentLabel.VERIFY_DELETE.value
NOT_DELETION = IntentLabel.NOT_DELETION.value
AMBIGUOUS = IntentLabel.AMBIGUOUS.value
CLASSES = tuple(label.value for label in IntentLabel)
DELETION_CLASSES = tuple(label.value for label in DELETION_INTENTS)


# ------------------------------------------------------------------ lexicon

# Base verbs and nouns that express a deletion request.
_DEL_BASE = (
    r"delete|erase|remove|purge|wipe|deletion|erasure|removal"
    r"|eliminar|eliminaci[oó]n|borrar|borrado|supresi[oó]n|suprimir"          # es
    r"|excluir|exclus[aã]o|apagar|elimina[cç][aã]o"                          # pt
    r"|supprimer|suppression|effacer|effacement"                             # fr
    r"|l[oö]schen|l[oö]schung|entfernen"                                     # de
    r"|cancellare|cancellazione|eliminazione"                                # it
    r"|verwijderen|verwijdering"                                             # nl
)
_CJK_DEL = r"削除|삭제|删除|刪除|消去|탈퇴|退会|注销|註銷"
# Past / participle forms: deletion only inside a request frame.
_DEL_PAST = r"deleted|erased|removed|purged|wiped|closed|eliminad[oa]s?|exclu[ií]d[oa]s?|supprim[ée]e?s?|gel[oö]scht"
_CLOSE = r"close|cerrar|encerrar|fermer|cl[oô]turer|schlie(?:ss|ß)en|chiudere"
_ACCOUNT = r"account|profile|cuenta|conta|compte|konto|profil|perfil|アカウント|계정"

_RE_DEL_BASE = re.compile(rf"\b(?:{_DEL_BASE})\b|{_CJK_DEL}", re.I)
_RE_DEL_ANY = re.compile(rf"\b(?:{_DEL_BASE}|{_DEL_PAST}|{_CLOSE}|deleting|removing|erasing|closing)\b|{_CJK_DEL}", re.I)
_RE_CLOSE_ACCOUNT = re.compile(rf"\b(?:{_CLOSE})\b.{{0,40}}(?:\b(?:{_ACCOUNT})\b|アカウント|계정)|\bclose (?:it|this)\b", re.I)
_RE_PROGRESSIVE = re.compile(r"\b(?:i'?m|i am|we are|we're)\s+(?:deleting|closing|removing|erasing)\b", re.I)
# "would like it permanently deleted", "have its data deleted", "to be erased", "like it closed"
_RE_FRAME_PAST = re.compile(
    rf"\b(?:like|want|have|get|need)\b(?:\s+\S+){{0,6}}?\s+(?:{_DEL_PAST})\b"
    rf"|\bto be\s+(?:\w+\s+)?(?:{_DEL_PAST})\b",
    re.I,
)
# Data that survived a deletion: "traces", "left behind", "can still be found".
_REMNANT = (
    r"traces?|left behind|leftovers?|remain(?:s|ing)?|residual"
    r"|still (?:exists?|existed|appears?|shows?|works?|recogni[sz]ed|visible|there|points?)"
    r"|can still (?:\w+ )?(?:find|found|see|be found|be seen)"
)
_RE_REMNANT = re.compile(rf"\b(?:{_REMNANT})\b", re.I)
# Past or state wording used inside a verify request.
_RE_DEL_STATE = re.compile(
    rf"\b(?:{_DEL_PAST}|gone|deletion|erasure|removal|eliminaci[oó]n|exclus[aã]o|suppression|{_REMNANT})\b|{_CJK_DEL}",
    re.I,
)
_RE_VERIFY = re.compile(
    r"\b(?:verify|confirm|confirmation|check|inspect|audit|tell me whether|tell me if|make sure"
    r"|comprobar|comprueben|verificar|confirmar|v[ée]rifier|confirmer|pr[uü]fen|best[aä]tigen)\b"
    r"|確認|확인",
    re.I,
)
# A verify clause that still asks to act: "complete the deletion if needed".
_RE_ACT_ON = re.compile(
    r"\b(?:complete|completar|finish|finalize|terminar|finalizar|process|begin|start|proceed with)\b"
    r"(?:\s+\S+){0,3}?\s+(?:the\s+|la\s+|el\s+|a\s+)?(?:deletion|erasure|removal|eliminaci[oó]n|exclus[aã]o|suppression)\b",
    re.I,
)

_RE_NEGATOR = re.compile(
    r"\b(?:not|never|without|rather than|instead of|no(?!\s+longer)|nor|n[aã]o|nunca|sin|sem|pas|ne|nicht|kein\w*)\b"
    r"|n['’]t\b",
    re.I,
)
_RE_CJK_NEG = re.compile(r"(?:削除|삭제|删除|刪除)\S{0,6}(?:しないで|しない|不要|하지\s*마|하지\s*않|원하지\s*않)|不要删除|不要刪除")

_RE_KEEP = re.compile(
    rf"\b(?:keep|leave|retain|maintain)\s+(?:the|my|this)\s+(?:{_ACCOUNT})\b(?!\s+reference)"
    rf"|\b(?:{_ACCOUNT})\b.{{0,30}}\b(?:active|open|in place|as it is)\b"
    r"|\bleave\b.{0,40}\bin place\b"
    r"|\bcontinue (?:using|to use)\b"
    r"|\bstill (?:need|use|want)\b",
    re.I,
)
_RE_MARKETING = re.compile(r"\b(?:marketing|promotional|newsletters?|mailing lists?|promo)\b", re.I)
_RE_ONLY = re.compile(r"\bonly\b|\bjust\b|\bsolo\b|\bapenas\b|\bseulement\b|\buniquement\b", re.I)

# Other (non-deletion) requests. Each needs a request frame in the same clause.
_RE_REQUEST_FRAME = re.compile(
    r"\b(?:please|could you|can you|would you|i'?d like|i would like|i need|i want|need help|help me"
    r"|por favor|pueden|podr[ií]an|merci de|veuillez|bitte)\b|ください|주세요",
    re.I,
)
_RE_OTHER = re.compile(
    r"\b(?:update|replace|change|amend|modify)\b"
    r"|\bcorrect (?:it|my|this|the (?:spelling|name|surname|email|address|phone))\b"
    r"|\bfix (?:it|my|the)\b"
    r"|\bdownload\b|\bportable format\b|\bexport (?:my|of my)\b"
    r"|\b(?:send|give|provide|need|want|get)\s+(?:me\s+)?(?:a\s+)?cop(?:y|ies)\b"
    r"|\bwhat (?:personal )?(?:information|data)\b|\binformation request\b|\baccess request\b"
    r"|\breset(?:ting)?\b|\blog ?in\b|\bpassword\b"
    r"|\binvoices?\b|\breceipts?\b"
    r"|\b(?:stop|unsubscribe|opt out)\b",
    re.I,
)
_RE_STATEMENT_OTHER = re.compile(r"\binformation request\b|\bnot a request to\b", re.I)

# Decision 5: text that tries to instruct the auditor is never trusted as a plain request.
_RE_INSTRUCTION = re.compile(
    r"(?:^|\n|[\[<(])\s*(?:system|assistant|developer|admin)\s*[:\]>]"
    r"|\b(?:mark|set|report|flag|record)\b[^.\n]{0,30}\bas\s+(?:complete|completed|not_applicable)\b"
    r"|\bignore\b[^.\n]{0,40}\b(?:instructions?|rules?|polic(?:y|ies)|evidence|prompt|above|previous)\b"
    r"|\b(?:deletion_status|steps_json)\b"
    r"|\byou are (?:an? )?(?:ai|assistant|agent|model|auditor)\b",
    re.I,
)

_RE_SENTENCE = re.compile(r"(?<=[.!?。？！])\s*")
_RE_CLAUSE = re.compile(
    r"[,;:、，；]|\s[-–—]\s|\b(?:but|so|however|although|though|pero|mas|mais|aber|ma)\b",
    re.I,
)


# ------------------------------------------------------------------ result

@dataclass
class ClauseSignals:
    text: str
    signals: list[str] = field(default_factory=list)


@dataclass
class IntentResult:
    label: str
    is_deletion: bool
    flagged: bool                     # True when the label needs review (AMBIGUOUS)
    reasons: list[str] = field(default_factory=list)
    clauses: list[ClauseSignals] = field(default_factory=list)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def split_clauses(text: str) -> list[str]:
    clauses = []
    for sentence in _RE_SENTENCE.split(_normalize(text)):
        for part in _RE_CLAUSE.split(sentence):
            part = part.strip(" \t\r\n.!?。？！¿¡\"'")
            if part:
                clauses.append(part)
    return clauses


def _is_negated(clause: str) -> bool:
    if _RE_CJK_NEG.search(clause):
        return True
    for neg in _RE_NEGATOR.finditer(clause):
        window = clause[neg.end():neg.end() + 60]
        if _RE_DEL_ANY.search(" ".join(window.split()[:6])):
            return True
    return False


def clause_signals(clause: str) -> list[str]:
    signals: list[str] = []
    negated = _is_negated(clause)
    marketing_only = bool(_RE_MARKETING.search(clause)) and (
        bool(_RE_ONLY.search(clause)) or not re.search(rf"\b(?:{_ACCOUNT}|data|details|information)\b", clause, re.I)
    )
    if negated:
        signals.append("negated")
    if marketing_only:
        signals.append("marketing")

    if not negated and not marketing_only:
        verify = bool(_RE_VERIFY.search(clause)) and bool(_RE_DEL_STATE.search(clause))
        if verify:
            signals.append("verify")
        base = _RE_DEL_BASE.search(clause)
        if verify:
            # Inside a verify clause a deletion noun is a state, unless the clause asks to act on it.
            asks = bool(_RE_ACT_ON.search(clause))
        else:
            asks = bool(base) or bool(_RE_CLOSE_ACCOUNT.search(clause)) or bool(_RE_FRAME_PAST.search(clause))
        if asks or _RE_PROGRESSIVE.search(clause):
            signals.append("delete")
        elif not verify and _RE_DEL_ANY.search(clause):
            signals.append("deleted_context")
        if _RE_REMNANT.search(clause):
            signals.append("remnant")

    if _RE_KEEP.search(clause):
        signals.append("keep")
    if _RE_STATEMENT_OTHER.search(clause) or (_RE_OTHER.search(clause) and _RE_REQUEST_FRAME.search(clause)):
        if "delete" not in signals and "verify" not in signals:
            signals.append("other")
    return signals


def has_instruction(text: str) -> bool:
    return bool(_RE_INSTRUCTION.search(_normalize(text)))


def classify(text: str) -> IntentResult:
    clauses = [ClauseSignals(c, clause_signals(c)) for c in split_clauses(text)]
    seen = {s for c in clauses for s in c.signals}
    positive = {"delete", "verify"} & seen
    negative = {"negated", "keep", "marketing", "other"} & seen
    reasons = sorted(seen)

    if has_instruction(text):
        label = AMBIGUOUS
        reasons.append("instruction_pattern")
    elif positive and negative:
        label = AMBIGUOUS
    elif "delete" in positive:
        label = DELETE
    elif "verify" in positive:
        label = VERIFY_DELETE
    elif negative:
        label = NOT_DELETION
    elif {"deleted_context", "remnant"} <= seen:
        # A past deletion plus data that survived it: the person wants the rest removed.
        label = DELETE
        reasons.append("remnant_after_deletion")
    else:
        label = AMBIGUOUS
        reasons.append("no_signal")
    return IntentResult(label, label in DELETION_CLASSES, label == AMBIGUOUS, reasons, clauses)


def treat_as_deletion(result: IntentResult) -> bool:
    """Phase 1 policy: AMBIGUOUS counts as deletion (flagged). Phase 4 replaces this with the LLM."""
    return result.is_deletion or result.label == AMBIGUOUS
