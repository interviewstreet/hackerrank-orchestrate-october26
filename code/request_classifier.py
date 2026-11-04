"""
request_classifier.py — Stage 0 of the deletion-audit pipeline.

Decides whether a request_text actually authorises deletion (§6.5).

Rule-based, no LLM, deterministic.  Four signal families are matched in
English, Spanish, Portuguese, French, Japanese and Korean:

  DELETION   — asks to delete / erase / remove / close the account or data
  NEGATION   — a deletion term that is negated ("don't delete",
               "ne supprimez pas", "삭제하지 마", "削除しないで", ...)
  KEEP       — asks to keep / continue / leave the account
  OTHER      — a non-deletion intent: access, copy, download/export,
               correct/change/update, marketing opt-out, login help

Decision:
  * NEGATION or KEEP present:
        deletion term outside the negated span -> UNCERTAIN (conflict)
        otherwise                              -> NOT_APPLICABLE
  * DELETION present:
        with an OTHER intent                   -> UNCERTAIN (mixed request)
        otherwise                              -> IS_DELETION
  * only OTHER present                         -> NOT_APPLICABLE
  * nothing matched                            -> UNCERTAIN
"""
from __future__ import annotations

import re
import unicodedata

from models import ClassificationResult

_F = re.IGNORECASE

# ---------------------------------------------------------------------------
# Deletion terms
# ---------------------------------------------------------------------------
_DELETION = [
    # English
    r"\bdelet\w*",
    r"\beras\w*",
    r"\bremov\w*\b(?!\s+(?:me|us)\s+from)",          # "remove me from <list>" is an opt-out
    r"\bclos(?:e|ing)\s+(?:my|this|the)\s+account",
    # asks to confirm a deleted / unlinkable state
    r"\b(?:is|are)\s+(?:now\s+)?gone\b",
    r"\bcan(?:not|'t)\s+(?:be\s+used\s+to\s+)?identify\s+me\b",
    r"\banonymi[sz]\w*", r"\bde-?identif\w*",
    # Spanish / Portuguese (shared stems)
    r"\beliminaci[oó]n\b", r"\belimina[çc][aã]o\b", r"\belimin\w+",
    r"\bborr\w+", r"\bsupresi[oó]n\b", r"\bsuprim\w+",
    r"\bcerrar\s+(?:mi|la)\s+cuenta",
    r"\bexclus[aã]o\b", r"\bexclu\w+", r"\bapag\w+",
    r"\bencerr\w+\s+(?:a|minha)\s+conta",
    # French
    r"\bsuppression\b", r"\bsupprim\w+", r"\beffac\w+",
    r"\b(?:fermer|fermez|cl[oô]turer|cl[oô]turez)\s+(?:mon|le)\s+compte",
    # Japanese
    r"削除", r"消去", r"退会",
    # Korean
    r"삭제", r"탈퇴", r"파기",
]

# Stems used inside negation patterns
_EN_DEL = r"(?:delet|eras|remov|clos)\w*"
_ES_DEL = r"(?:elimin|borr|suprim|cerr)\w*"
_PT_DEL = r"(?:exclu|apag|elimin|encerr|delet)\w*"
_FR_DEL = r"(?:supprim|effac|ferm|cl[oô]tur)\w*"
# Up to 4 intervening words, not crossing punctuation
_GAP = r"(?:\s+[\w'-]+){0,4}?\s+"

# ---------------------------------------------------------------------------
# Negated deletion
# ---------------------------------------------------------------------------
_NEGATION = [
    # English: don't/do not/not/never/without ... delete
    rf"\b(?:don't|do not|does not|did not|not|never|without|no need to)(?:{_GAP}|\s+){_EN_DEL}",
    # Spanish: no (quiero) eliminen ...
    rf"\bno(?:{_GAP}|\s+){_ES_DEL}",
    # Portuguese: não (quero) exclua ...
    rf"\bn[aã]o(?:{_GAP}|\s+){_PT_DEL}",
    # French: ne supprimez pas / n'effacez pas / ne pas supprimer
    rf"\bn(?:e\s+|')(?:pas\s+)?{_FR_DEL}",
    # Japanese
    r"(?:削除|消去|退会)(?:しないで|しない|せず|は不要|しなくて)",
    # Korean
    r"(?:삭제|탈퇴|파기)(?:를|는|은)?\s*(?:하지\s*(?:마|말|않)|원하지\s*않|안\s*해)",
]

# ---------------------------------------------------------------------------
# Keep / continue / leave the account
# ---------------------------------------------------------------------------
_KEEP = [
    # English
    r"\bkeep\s+(?:the|my|this)\s+(?:account|profile)",
    r"\bleave\s+(?:the|my|this)\s+(?:account|profile)",
    r"\bcontinue\s+(?:using|to\s+use)",
    r"\bstill\s+(?:use|need|want)\b",
    # Spanish
    r"\b(?:mantener|mantengan|conservar|conserven)\s+(?:mi|la)\s+cuenta",
    r"\bseguir\s+usando",
    # Portuguese
    r"\b(?:manter|mantenham|conservar)\s+(?:a|minha)\s+conta",
    r"\bcontinuar\s+(?:usando|a\s+usar|utilizando)",
    # French
    r"\b(?:garder|gardez|conserver|conservez|laisser|laissez)\s+(?:mon|le)\s+compte",
    r"\bcontinuer\s+[àa]\s+utiliser",
    # Japanese
    r"アカウント(?:は|を)(?:そのまま|残し|維持)",
    r"使い続け", r"引き続き(?:利用|使用)",
    # Korean
    r"계정(?:은|을)?\s*(?:유지|그대로)",
    r"계속\s*(?:사용|이용)",
]

# ---------------------------------------------------------------------------
# Non-deletion intents
# ---------------------------------------------------------------------------
_OTHER = [
    # English — access / copy / export
    r"\bwhat\s+(?:personal\s+)?(?:information|data)\s+(?:you|do\s+you)\s+(?:hold|have|store)",
    r"\binformation\s+request\b", r"\baccess\s+(?:to\s+)?my\s+(?:data|information)",
    # copy / download only when the person wants to *receive* something
    r"\b(?:send|give|provide|email|mail)\s+me\s+(?:a\s+|the\s+)?cop(?:y|ies)\b",
    r"\b(?:i|we)\s+(?:need|want|would\s+like|'d\s+like|request)\s+(?:a\s+|to\s+get\s+a\s+)?cop(?:y|ies)\b",
    r"\b(?:i|we)\s+(?:need|want|would\s+like|'d\s+like)\s+to\s+download\b",
    r"\bdownload\s+(?:my|our)\b", r"\bportable\b", r"\bexport\s+my\b",
    # English — correct / change / update
    r"\b(?:correct|fix|update|change|replace)\s+(?:it|my|the|this)\b",
    r"\bupdated\b", r"\bmisspel\w*", r"\bout\s+of\s+date\b", r"\bincorrect\b",
    # English — marketing opt-out
    r"\bmarketing\b", r"\bpromotional\b", r"\bnewsletters?\b", r"\bunsubscribe\b",
    r"\bopt[- ]?out\b", r"\bmailing\s+lists?\b",
    # English — login help
    r"\blog\s?in\b", r"\bpassword\b", r"\breset\w*", r"\bsign\s+in\b", r"\bcan't\s+access\b",
    # Spanish
    r"\bcopia\b", r"\bdescarg\w+", r"\bacceso\s+a\s+mis\s+datos", r"\bcorregir\b",
    r"\bactualiz\w+", r"\bcambi\w+", r"\bpublicidad\b", r"\bcontrase[ñn]a\b",
    r"\biniciar\s+sesi[oó]n\b",
    # Portuguese
    r"\bc[oó]pia\b", r"\bbaixar\b", r"\bacesso\s+aos\s+meus\s+dados", r"\bcorrigir\b",
    r"\batualiz\w+", r"\balter\w+", r"\bpublicidade\b", r"\bsenha\b",
    # French
    r"\bcopie\b", r"\bt[ée]l[ée]charg\w+", r"\bacc[èe]s\s+[àa]\s+mes\s+donn[ée]es",
    r"\bcorrig\w+", r"\bmettre\s+[àa]\s+jour\b", r"\bmodifi\w+", r"\bpublicit[ée]\b",
    r"\bd[ée]sabonn\w+", r"\bmot\s+de\s+passe\b", r"\bconnexion\b",
    # Japanese
    r"コピー", r"ダウンロード", r"開示", r"修正", r"訂正", r"変更", r"更新",
    r"配信停止", r"メールマガジン", r"広告", r"パスワード", r"ログイン",
    # Korean
    r"사본", r"다운로드", r"열람", r"수정", r"정정", r"변경", r"업데이트",
    r"마케팅", r"광고", r"수신\s*거부", r"비밀번호", r"로그인",
]

_DELETION_RE = [re.compile(p, _F) for p in _DELETION]
_NEGATION_RE = [re.compile(p, _F) for p in _NEGATION]
_KEEP_RE = [re.compile(p, _F) for p in _KEEP]
_OTHER_RE = [re.compile(p, _F) for p in _OTHER]


# Conjunctions that start a new clause (a second, separate request)
_CONJ = r"\b(?:and|but|then|also|y|pero|e|mas|et|mais|puis)\b"


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return text.replace("’", "'").replace("‘", "'")


def _find(patterns: list[re.Pattern], text: str) -> list[re.Match]:
    return [m for p in patterns for m in p.finditer(text)]


def classify_request(request_text: str) -> ClassificationResult:
    """Classify *request_text* as IS_DELETION, NOT_APPLICABLE or UNCERTAIN."""
    text = _normalise(request_text)

    neg = _find(_NEGATION_RE, text)
    keep = _find(_KEEP_RE, text)
    other = _find(_OTHER_RE, text)
    dele = _find(_DELETION_RE, text)

    # Deletion terms that sit inside a negated span don't count as a request
    neg_spans = [m.span() for m in neg]
    positive_del = [
        m for m in dele
        if not any(s <= m.start() < e for s, e in neg_spans)
    ]

    # A non-deletion term right after a deletion verb is the *object* being
    # deleted ("remove any remaining copy", "eliminen cualquier copia"),
    # not a separate intent: within 4 words, same clause.
    def _is_deletion_object(o: re.Match) -> bool:
        for d in positive_del:
            gap = text[d.end():o.start()]
            if d.end() <= o.start() and not re.search(r"[.,;:!?。、]", gap) \
                    and not re.search(_CONJ, gap, _F) \
                    and len(gap.split()) <= 4:
                return True
        return False

    other = [o for o in other if not _is_deletion_object(o)]

    def kw(ms: list[re.Match]) -> list[str]:
        out: list[str] = []
        for m in sorted(ms, key=lambda m: m.start()):
            if m.group(0) not in out:
                out.append(m.group(0))
        return out

    signals = (
        [f"NEGATION:{k}" for k in kw(neg)]
        + [f"KEEP:{k}" for k in kw(keep)]
        + [f"DELETION:{k}" for k in kw(positive_del)]
        + [f"OTHER:{k}" for k in kw(other)]
    )
    R = ClassificationResult

    if neg or keep:
        if positive_del:
            return R(R.UNCERTAIN, "LOW", signals,
                     "deletion requested but also negated / keep-account phrase")
        return R(R.NOT_APPLICABLE, "HIGH", signals,
                 "deletion negated or asks to keep the account")

    if positive_del:
        if other:
            return R(R.UNCERTAIN, "LOW", signals,
                     "deletion requested together with a non-deletion intent")
        return R(R.IS_DELETION, "HIGH", signals, "deletion requested")

    if other:
        return R(R.NOT_APPLICABLE, "HIGH", signals, "non-deletion intent only")

    return R(R.UNCERTAIN, "LOW", signals, "no deletion or non-deletion signal matched")
