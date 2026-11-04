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

# "<remove> me / us / my email ... from <up to 3 words> list|marketing|..."
_OPTOUT_TAIL = (
    r"\s+(?:me|us|my\s+(?:e-?mail(?:\s+address)?|address|name|(?:phone\s+)?number))"
    r"\s+from\s+(?:[\w'-]+\s+){0,3}?"
    r"(?:lists?|mailing|marketing|newsletters?|promotions?|promotional|campaigns?)\b"
)

# ---------------------------------------------------------------------------
# Deletion terms
# ---------------------------------------------------------------------------
_DELETION = [
    # English
    r"\bdelet\w*",
    r"\beras\w*",
    # "remove me / my email from <marketing list>" is an opt-out, not deletion
    rf"\bremov\w*\b(?!{_OPTOUT_TAIL})",
    r"\bclos(?:e|ing)\s+(?:my|this|the)\s+account",
    # asks to confirm a deleted / unlinkable state
    r"\b(?:is|are)\s+(?:now\s+)?gone\b",
    r"\bcan(?:not|'t)\s+(?:be\s+used\s+to\s+)?identify\s+me\b",
    r"\banonymi[sz]\w*", r"\bde-?identif\w*",
    # Spanish / Portuguese (shared stems)
    r"\beliminaci[oó]n\b", r"\belimina[çc][aã]o\b", r"\belimin\w+",
    r"\bborr\w+", r"\bsupresi[oó]n\b", r"\bsuprim\w+",
    r"\bcerrar\s+(?:mi|la)\s+cuenta",
    # Portuguese "excluir" only — a bare exclu- stem would match English "exclude"
    r"\bexclus[aã]o\b", r"\bexclu(?:ir|a|am)\b", r"\bapag\w+",
    r"\bencerr\w+\s+(?:a|minha)\s+conta",
    # French
    r"\bsuppression\b", r"\bsupprim\w+", r"\beffac\w+",
    r"\b(?:fermer|fermez|cl[oô]turer|cl[oô]turez)\s+(?:mon|le)\s+compte",
    # Japanese
    r"削除", r"消去", r"退会",
    # Korean
    r"삭제", r"탈퇴", r"파기",
]

# Deletion verbs used inside negation patterns
_EN_DEL = r"(?:delet|eras|remov|clos)\w*"
_EN_DEL_NOUN = r"(?:(?:account\s+)?deletion|erasure|removal|closure)"
# Imperative / infinitive forms only, so a negated *description* ("no fue
# eliminada", "n'a pas été supprimé") does not count.
_ES_DEL = r"(?:elimin(?:en|e|ar)|borr(?:en|e|ar)|suprim(?:an|a|ir)|cierr(?:en|e)|cerrar)\b"
_PT_DEL = r"(?:exclu(?:a|am|ir)|apagu(?:e|em)|apagar|elimin(?:e|em|ar)|encerr(?:e|em|ar))\b"
_FR_DEL = r"(?:supprim(?:ez|er)|effac(?:ez|er)|ferm(?:ez|er)|cl[oô]tur(?:ez|er))\b"

# ---------------------------------------------------------------------------
# Negated deletion — only negations that are *instructions* ("don't delete",
# "do not close", "not asking for deletion"), never descriptions
# ("was not removed", "has not been erased", "do not hesitate to delete").
# ---------------------------------------------------------------------------
_NEGATION = [
    # English imperative: don't / do not / never [please|ever] delete
    rf"\b(?:don't|do\s+not|never)\s+(?:please\s+|ever\s+|actually\s+)?{_EN_DEL}",
    # English wish: I / we don't want (my account / it) (to be) deleted
    rf"\b(?:i|we)\s+(?:don't|do\s+not)\s+want\s+"
    rf"(?:(?:my|the|this|our|it)\s+)?(?:(?:account|data|profile|information)\s+)?"
    rf"(?:to\s+be\s+|to\s+)?{_EN_DEL}",
    # English: not asking for / not requesting / not a request to (erase|deletion)
    rf"\bnot\s+(?:asking|requesting|a\s+request)\s+(?:for|to)\s+(?:an?\s+|the\s+)?"
    rf"(?:{_EN_DEL_NOUN}|{_EN_DEL})",
    rf"\bnot\s+requesting\s+(?:an?\s+)?{_EN_DEL_NOUN}",
    # English condition on another request: "... without removing my records"
    rf"\bwithout\s+{_EN_DEL}",
    rf"\bno\s+need\s+to\s+{_EN_DEL}",
    # Spanish: no eliminen / no quiero (que) eliminar ...
    rf"\bno\s+(?:(?:quiero|deseo)\s+(?:que\s+)?)?(?:(?:me|mi|la|los)\s+)?{_ES_DEL}",
    # Portuguese: não exclua / não quero (que) excluir ...
    rf"\bn[aã]o\s+(?:(?:quero|desejo)\s+(?:que\s+)?)?(?:(?:a|minha)\s+)?{_PT_DEL}",
    # French: ne supprimez pas / n'effacez pas / ne pas supprimer
    rf"\bn(?:e\s+|')(?:pas\s+)?{_FR_DEL}",
    # Japanese: 削除しないで(ください) / 削除は不要 / 削除しなくていい
    r"(?:削除|消去|退会)(?:しないで|は不要|しなくて(?:いい|よい|結構))",
    # Korean: 삭제하지 마(세요) / 삭제를 원하지 않 / 삭제하지 않아도
    r"(?:삭제|탈퇴|파기)(?:를|는|은)?\s*(?:하지\s*(?:마|말)|원하지\s*않|하지\s*않아도)",
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


# Conjunctions that start a new clause (a second, separate request):
# and / but / or / then in EN, ES (y, pero, o), PT (e, mas, ou), FR (et, mais,
# ou, puis), plus JA (または, あるいは, もしくは) and KO (또는, 아니면, 혹은).
# JA/KO have no word boundaries, so they are matched without \b.
_CONJ = (
    r"\b(?:and|but|or|then|also|y|pero|o|e|mas|ou|et|mais|puis)\b"
    r"|または|あるいは|もしくは|또는|아니면|혹은"
)


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
