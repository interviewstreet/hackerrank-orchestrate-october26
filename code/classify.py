"""Deletion-intent classification with deterministic fast paths."""
from __future__ import annotations
import logging, os
from code import cache as default_cache

DELETION_SIGNALS=("delete","deletion","erase","erasure","remove","close my account","right to be forgotten","gdpr","data removal","wipe","eliminar","eliminación","borrar","suprimir","cerrar mi cuenta","derecho al olvido","supprimer","suppression","effacer","fermer mon compte","droit à l'oubli","löschen","konto schließen","vergessenwerden","excluir","exclusão","apagar","encerrar minha conta","削除","アカウント削除","삭제")
NON_DELETION_SIGNALS=("access","export","download my data","portable format","marketing","unsubscribe","opt out","opt-out","correction","update my data","right to access","leave the account active","keep the account","without removing","copy of","leave my profile","change the email address","continue using")

def classify_request(request_text: str, case_id: str, cache=default_cache) -> str:
    key=cache.make_key(case_id,request_text)
    hit=cache.get(key)
    if hit in {"DELETION","NOT_APPLICABLE"}: return hit
    text=request_text.casefold()
    if any(s.casefold() in text for s in DELETION_SIGNALS): result="DELETION"
    elif any(s.casefold() in text for s in NON_DELETION_SIGNALS): result="NOT_APPLICABLE"
    else:
        try:
            from google import genai
            from google.genai import types
            client=genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
            response=client.models.generate_content(model="gemini-2.5-flash",contents=("Classify this privacy request. Reply with exactly one word: DELETION or NOT_APPLICABLE.\n\n"+request_text),config=types.GenerateContentConfig(temperature=0))
            candidate=(response.text or "").strip().upper()
            result=candidate if candidate in {"DELETION","NOT_APPLICABLE"} else "DELETION"
        except Exception as exc:
            logging.getLogger(__name__).error("Gemini classification failed: %s",type(exc).__name__)
            result="DELETION"
    cache.set(key,result)
    return result
