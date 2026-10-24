"""Model labels for request texts the clause rules leave AMBIGUOUS (plan 7.3).

* Only AMBIGUOUS texts are sent; rules win whenever they are confident.
* Texts are identified by ``text_id`` = SHA-256 prefix of the text, never by case id.
* Each text is screened first (D20); a screened text is not sent and stays AMBIGUOUS.
* Batches of ``config.INTENT_BATCH_SIZE``; the answer is ``schema.IntentBatch`` (enum labels,
  exact-substring quotes, exact coverage). A ``low`` confidence label is not used: the text
  stays AMBIGUOUS (counted as deletion and flagged, as in Phase 1).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import config
import safety
from llm_client import LLMClient, render_prompt
from schema import IntentBatch

PROMPT = config.PROMPT_VERSIONS["intent"]


def text_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass
class ModelLabel:
    label: str | None          # DELETE | VERIFY_DELETE | NOT_DELETION, None when not used
    flag: str                  # model_high | model_low | screened | fallback:<flag>
    quote: str = ""


def _messages(batch: dict[str, str]) -> list[dict]:
    blocks = "\n\n".join(safety.wrap(f"text_id={tid}", text) for tid, text in sorted(batch.items()))
    system, user = render_prompt(PROMPT, SCHEMA=json.dumps(IntentBatch.model_json_schema(), sort_keys=True),
                                 TEXTS=blocks)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def label_texts(texts: list[str], client: LLMClient) -> dict[str, ModelLabel]:
    """Map each distinct text to its model label (keyed by text_id)."""
    out: dict[str, ModelLabel] = {}
    pending: dict[str, str] = {}
    for text in texts:
        tid = text_id(text)
        if tid in out or tid in pending:
            continue
        if safety.screen(text):
            out[tid] = ModelLabel(None, "screened")
        else:
            pending[tid] = text
    ids = sorted(pending)
    for start in range(0, len(ids), config.INTENT_BATCH_SIZE):
        batch = {tid: pending[tid] for tid in ids[start:start + config.INTENT_BATCH_SIZE]}
        ref = text_id("".join(sorted(batch)))
        result = client.structured("intent", ref, _messages(batch), IntentBatch, {"texts": batch}, PROMPT)
        if not isinstance(result.value, IntentBatch):
            for tid in batch:
                out[tid] = ModelLabel(None, f"fallback:{result.flag}")
            continue
        for item in result.value.items:
            if item.confidence == "high":
                out[item.text_id] = ModelLabel(item.label, "model_high", item.quote)
            else:
                out[item.text_id] = ModelLabel(None, "model_low", item.quote)
    return out
