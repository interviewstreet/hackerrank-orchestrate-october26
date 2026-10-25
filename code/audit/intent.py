"""Request-intent classification: DELETE vs NON_DELETE (NOT_APPLICABLE).

Primary signal is the meaning of request_text. A multilingual rule-based
classifier handles clear cases and powers --no-llm; an LLM (batched, cached,
temperature 0) can classify every unique text when a key is configured.
system_activity CLASSIFY_REQUEST rows are a cross-check only.
"""
import re

# Explicit non-deletion phrasing (checked first; these win over delete words)
NON_DELETE_PATTERNS = [
    r"not a request to erase", r"not asking for deletion", r"don'?t delete",
    r"do not delete", r"please don'?t delete or change",
    r"what personal information you hold", r"what data do you hold",
    r"send me a copy", r"copy of (the|my|last) .*?(information|invoices)",
    r"i need a copy", r"download my (account )?information",
    r"download my data", r"in a portable format",
    r"remove me from marketing", r"marketing lists only",
    r"stop the promotional", r"stop marketing",
    r"misspelled", r"surname is", r"correct my",
    r"change the email address", r"change my email",
    r"replace it with the new", r"mobile number on my profile is out of date",
    r"leave the account active", r"still use it", r"still need the account",
    r"i still want receipts", r"resetting the login", r"reset my login",
    r"can'?t access my profile and need help",
]

# Deletion stems across the languages present in the dataset
DELETE_PATTERNS = [
    r"\bdelete\b", r"\bdeletion\b", r"\berase\b", r"\berased\b",
    r"\bremove my account\b", r"\bremove the profile\b", r"\bclose (my|this) account\b",
    r"\bclosed\b.*\baccount\b", r"permanently deleted", r"account-deletion",
    r"remove my account", r"deleting my account",
    # Spanish / Portuguese / French
    r"eliminar mi cuenta", r"eliminaci[oó]n", r"exclus[aã]o permanente",
    r"suppression", r"supprimer",
    # Japanese / Korean (deletion request)
    r"削除", r"삭제",
]


def classify_rule(text):
    t = (text or "").lower()
    for pat in NON_DELETE_PATTERNS:
        if re.search(pat, t):
            return {"intent": "NON_DELETE",
                    "reason": f"non-deletion pattern: {pat}", "source": "rules"}
    for pat in DELETE_PATTERNS:
        if re.search(pat, t):
            return {"intent": "DELETE",
                    "reason": f"deletion pattern: {pat}", "source": "rules"}
    return {"intent": "DELETE", "reason": "default: deletion-audit request",
            "source": "rules"}


def classify_texts(unique_texts, use_llm=True, client=None, batch_size=25):
    """Return {text: {intent, reason, source}} for each unique text."""
    results = {}
    if not use_llm:
        for text in unique_texts:
            results[text] = classify_rule(text)
        return results
    from .llm import LLMClient, LLMNotConfigured, PROMPT_PATH
    if client is None:
        try:
            client = LLMClient()
        except LLMNotConfigured as exc:
            print(f"WARNING: {exc} Falling back to rule-based intent.")
            for text in unique_texts:
                results[text] = classify_rule(text)
            return results
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    texts = list(unique_texts)
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        listing = "\n".join(f"{i}. {t}" for i, t in enumerate(batch))
        prompt = (f"{prompt_template}\n\nMessages to classify:\n{listing}\n")
        parsed = client.complete_json(prompt)
        by_id = {item.get("id"): item for item in parsed if isinstance(item, dict)}
        for i, text in enumerate(batch):
            item = by_id.get(i, {})
            intent = item.get("intent")
            if intent not in ("DELETE", "NON_DELETE"):
                results[text] = classify_rule(text)
            else:
                results[text] = {"intent": intent,
                                 "reason": str(item.get("reason", ""))[:200],
                                 "source": "llm"}
    client.save_usage_stats()
    return results
