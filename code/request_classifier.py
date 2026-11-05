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
# Each pattern is tagged with the intent it shows. The tag is only used to
# explain the decision (signals / reason); every intent counts the same.
ACCESS, CORRECTION, OPT_OUT, LOGIN = "access", "correction", "opt_out", "login"
_A, _C, _O, _L = ACCESS, CORRECTION, OPT_OUT, LOGIN

_OTHER_TAGGED = [
    # English — access / copy / export
    (_A, r"\bwhat\s+(?:personal\s+)?(?:information|data)\s+(?:you|do\s+you)\s+(?:hold|have|store)"),
    (_A, r"\binformation\s+request\b"), (_A, r"\baccess\s+(?:to\s+)?my\s+(?:data|information)"),
    # copy / download only when the person wants to *receive* something
    (_A, r"\b(?:send|give|provide|email|mail)\s+me\s+(?:a\s+|the\s+)?cop(?:y|ies)\b"),
    (_A, r"\b(?:i|we)\s+(?:need|want|would\s+like|'d\s+like|request)\s+(?:a\s+|to\s+get\s+a\s+)?cop(?:y|ies)\b"),
    (_A, r"\b(?:i|we)\s+(?:need|want|would\s+like|'d\s+like)\s+to\s+download\b"),
    (_A, r"\bdownload\s+(?:my|our)\b"), (_A, r"\bportable\b"), (_A, r"\bexport\s+my\b"),
    # English — correct / change / update
    (_C, r"\b(?:correct|fix|update|change|replace)\s+(?:it|my|the|this)\b"),
    (_C, r"\bupdated\b"), (_C, r"\bmisspel\w*"), (_C, r"\bout\s+of\s+date\b"), (_C, r"\bincorrect\b"),
    # English — marketing opt-out
    (_O, r"\bmarketing\b"), (_O, r"\bpromotional\b"), (_O, r"\bnewsletters?\b"), (_O, r"\bunsubscribe\b"),
    (_O, r"\bopt[- ]?out\b"), (_O, r"\bmailing\s+lists?\b"),
    # English — login help
    (_L, r"\blog\s?in\b"), (_L, r"\bpassword\b"), (_L, r"\breset\w*"), (_L, r"\bsign\s+in\b"),
    (_L, r"\bcan't\s+access\b"),
    # Spanish
    (_A, r"\bcopia\b"), (_A, r"\bdescarg\w+"), (_A, r"\bacceso\s+a\s+mis\s+datos"), (_C, r"\bcorregir\b"),
    (_C, r"\bactualiz\w+"), (_C, r"\bcambi\w+"), (_O, r"\bpublicidad\b"), (_L, r"\bcontrase[ñn]a\b"),
    (_L, r"\biniciar\s+sesi[oó]n\b"),
    # Portuguese
    (_A, r"\bc[oó]pia\b"), (_A, r"\bbaixar\b"), (_A, r"\bacesso\s+aos\s+meus\s+dados"), (_C, r"\bcorrigir\b"),
    (_C, r"\batualiz\w+"), (_C, r"\balter\w+"), (_O, r"\bpublicidade\b"), (_L, r"\bsenha\b"),
    # French
    (_A, r"\bcopie\b"), (_A, r"\bt[ée]l[ée]charg\w+"), (_A, r"\bacc[èe]s\s+[àa]\s+mes\s+donn[ée]es"),
    (_C, r"\bcorrig\w+"), (_C, r"\bmettre\s+[àa]\s+jour\b"), (_C, r"\bmodifi\w+"), (_O, r"\bpublicit[ée]\b"),
    (_O, r"\bd[ée]sabonn\w+"), (_L, r"\bmot\s+de\s+passe\b"), (_L, r"\bconnexion\b"),
    # Japanese
    (_A, r"コピー"), (_A, r"ダウンロード"), (_A, r"開示"), (_C, r"修正"), (_C, r"訂正"), (_C, r"変更"),
    (_C, r"更新"), (_O, r"配信停止"), (_O, r"メールマガジン"), (_O, r"広告"), (_L, r"パスワード"),
    (_L, r"ログイン"),
    # Korean
    (_A, r"사본"), (_A, r"다운로드"), (_A, r"열람"), (_C, r"수정"), (_C, r"정정"), (_C, r"변경"),
    (_C, r"업데이트"), (_O, r"마케팅"), (_O, r"광고"), (_O, r"수신\s*거부"), (_L, r"비밀번호"),
    (_L, r"로그인"),
]
_OTHER = [p for _, p in _OTHER_TAGGED]

_DELETION_RE = [re.compile(p, _F) for p in _DELETION]
_NEGATION_RE = [re.compile(p, _F) for p in _NEGATION]
_KEEP_RE = [re.compile(p, _F) for p in _KEEP]
_OTHER_RE = [re.compile(p, _F) for p in _OTHER]
_OTHER_INTENT = {rx: tag for rx, (tag, _) in zip(_OTHER_RE, _OTHER_TAGGED)}


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


# ---------------------------------------------------------------------------
# Language detection (explanation only — never used by the decision)
# ---------------------------------------------------------------------------
LANGUAGES = ("en", "es", "pt", "fr", "ja", "ko")

_KANA = re.compile(r"[぀-ヿ]")
_HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힯]")
_HAN = re.compile(r"[一-鿿]")

# Common short words, chosen so each one is typical of one language.
# Words shared by several languages (de, que, la, a, no ...) are left out.
_STOPWORDS = {
    "en": {"the", "and", "my", "i", "is", "please", "to", "of", "you", "it", "for",
           "this", "that", "with", "have", "me", "your", "am", "was", "all", "any",
           "account", "data", "delete", "remove", "information", "about", "be", "can"},
    "es": {"el", "los", "las", "mi", "mis", "por", "favor", "cuenta", "datos", "y",
           "una", "con", "para", "quiero", "todos", "su", "sus", "del", "lo", "eliminen",
           "borren", "también", "información", "solicito", "ustedes", "cualquier"},
    "pt": {"os", "meu", "minha", "meus", "minhas", "conta", "dados", "uma", "com",
           "não", "quero", "você", "vocês", "do", "da", "dos", "das", "em", "seu",
           "sua", "também", "informações", "excluam", "apaguem", "solicito", "qualquer"},
    "fr": {"le", "les", "mon", "ma", "mes", "je", "vous", "compte", "données", "et",
           "avec", "pour", "est", "pas", "merci", "du", "des", "au", "aux", "votre",
           "vos", "supprimez", "toutes", "tous", "aussi", "informations", "demande"},
}
# Letters typical of one language add extra weight
_LETTER_HINTS = {"es": "ñ¿¡", "pt": "ãõ", "fr": "èêëîïœùûç«»"}
_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


def detect_language(request_text: str) -> str:
    """
    Return the language of *request_text*: en, es, pt, fr, ja or ko.

    Japanese and Korean are recognised by their scripts (kana / Han for
    Japanese, Hangul for Korean). For Latin-script text, each language
    scores 1 point per typical short word and 2 per typical letter; the
    highest score wins, ties go to the order en, es, pt, fr. Text with no
    signal at all (empty, only numbers) is "en".
    """
    text = _normalise(request_text).lower()
    if _HANGUL.search(text):
        return "ko"
    if _KANA.search(text) or _HAN.search(text):
        return "ja"
    words = _WORD.findall(text)
    scores = {lang: sum(w in sw for w in words) for lang, sw in _STOPWORDS.items()}
    for lang, letters in _LETTER_HINTS.items():
        scores[lang] += 2 * sum(text.count(ch) for ch in letters)
    best = max(scores.values())
    if best == 0:
        return "en"
    return next(lang for lang in ("en", "es", "pt", "fr") if scores[lang] == best)


# ---------------------------------------------------------------------------
# Explanation: signals and a one-sentence reason (never affect the label)
# ---------------------------------------------------------------------------
_INTENT_WORDS = {
    ACCESS: "to see or get a copy of their data",
    CORRECTION: "to correct or update their details",
    OPT_OUT: "to stop marketing messages",
    LOGIN: "for help signing in",
}


def _q(items: list[str], limit: int = 2) -> str:
    """'“a”, “b”' — the first *limit* matched phrases, quoted."""
    return ", ".join(f"“{i}”" for i in items[:limit])


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _reason(label: str, neg: list[str], keep: list[str], dele: list[str],
            other: dict[str, list[str]], conflict: bool) -> str:
    intents = [f"{_INTENT_WORDS[t]} ({_q(v)})" for t, v in other.items()]
    if label == ClassificationResult.IS_DELETION:
        return (f"Deletion request: the person asks to delete their data ({_q(dele)}) "
                "and nothing in the text refuses deletion or asks for something else.")
    if label == ClassificationResult.NOT_APPLICABLE:
        refusals = []
        if neg:
            refusals.append(f"say they do not want deletion ({_q(neg)})")
        if keep:
            refusals.append(f"want to keep the account ({_q(keep)})")
        if intents and refusals:
            return (f"Not a deletion request: the person asks {_join(intents)}, "
                    f"and they {_join(refusals)}.")
        if intents:
            return (f"Not a deletion request: the person only asks {_join(intents)}, "
                    "and never asks for deletion.")
        return f"Not a deletion request: they {_join(refusals)}."
    # UNCERTAIN
    if conflict:
        clash = [f"says not to delete ({_q(neg)})"] if neg else []
        clash += [f"asks to keep the account ({_q(keep)})"] if keep else []
        return (f"Unclear, needs review by a person: the text asks to delete ({_q(dele)}) "
                f"but also {_join(clash)}.")
    if dele:
        return (f"Unclear, needs review by a person: the text asks to delete ({_q(dele)}) "
                f"and also asks {_join(intents)}.")
    return ("Unclear, needs review by a person: no phrase asking for deletion "
            "or for anything else was found.")


def classify_request(request_text: str) -> ClassificationResult:
    """Classify *request_text* as IS_DELETION, NOT_APPLICABLE or UNCERTAIN."""
    result = _classify(request_text)
    result.language = detect_language(request_text)
    return result


def _classify(request_text: str) -> ClassificationResult:
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
    # Explanation: same matches, OTHER split by intent (first-seen order)
    other_by_intent: dict[str, list[str]] = {}
    for m in sorted(other, key=lambda m: m.start()):
        found = other_by_intent.setdefault(_OTHER_INTENT[m.re], [])
        if m.group(0) not in found:
            found.append(m.group(0))
    named = (
        [f"negation: {k}" for k in kw(neg)]
        + [f"keep: {k}" for k in kw(keep)]
        + [f"deletion: {k}" for k in kw(positive_del)]
        + [f"{t}: {k}" for t, ks in other_by_intent.items() for k in ks]
    )

    R = ClassificationResult

    def make(label: str, confidence: str, note: str, conflict: bool = False):
        return R(label, confidence, signals, note, signals=named,
                 reason=_reason(label, kw(neg), kw(keep), kw(positive_del),
                                other_by_intent, conflict))

    if neg or keep:
        if positive_del:
            return make(R.UNCERTAIN, "LOW",
                        "deletion requested but also negated / keep-account phrase",
                        conflict=True)
        return make(R.NOT_APPLICABLE, "HIGH", "deletion negated or asks to keep the account")

    if positive_del:
        if other:
            return make(R.UNCERTAIN, "LOW",
                        "deletion requested together with a non-deletion intent")
        return make(R.IS_DELETION, "HIGH", "deletion requested")

    if other:
        return make(R.NOT_APPLICABLE, "HIGH", "non-deletion intent only")

    return make(R.UNCERTAIN, "LOW", "no deletion or non-deletion signal matched")
