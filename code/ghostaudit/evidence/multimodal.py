"""PNG/PDF evidence -> RawRecords through a cached vision-LLM extraction (SPEC §6, task `extract_visual`).

The model only transcribes what the artifact shows into typed records; the shared classifier in
records.py decides the state, exactly as for structured evidence. Results are cached by content hash, so a
clean run replays them with no API key.
"""
from __future__ import annotations

import hashlib
import json
import logging

from ..config import PROMPTS_DIR, vision_grounding, vision_llm, vision_ocr_fallback
from ..loaders import parse_ts
from ..models import EvidenceFile
from . import ocr
from .records import RawRecord, system_for

log = logging.getLogger(__name__)
VISUAL_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf"}

SCHEMA = {
    "type": "object",
    "properties": {
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "system": {"type": "string"},
                    "observed_at": {"type": ["string", "null"]},
                    "fields": {"type": "object"},
                },
                "required": ["resource_id", "fields"],
            },
        }
    },
    "required": ["records"],
}


def prompt_for(ef: EvidenceFile) -> str:
    template = (PROMPTS_DIR / "extract_visual.md").read_text(encoding="utf-8")
    return (template.replace("{{file_path}}", str(ef.path))
            .replace("{{file_name}}", ef.path.name)
            .replace("{{origin}}", ef.origin)
            .replace("{{captured_at}}", ef.captured_at.isoformat().replace("+00:00", "Z")))


def records_from_payload(ef: EvidenceFile, payload: dict) -> list[RawRecord]:
    out: list[RawRecord] = []
    for item in (payload or {}).get("records", []):
        rid = str(item.get("resource_id") or "").strip()
        if not rid:
            continue
        fields = {str(k): v for k, v in (item.get("fields") or {}).items()}
        fields.setdefault("resource_id", rid)
        if rid.startswith("support_") and ef.path.suffix.lower() == ".pdf":
            # a support-platform document is itself an uploaded ticket file
            fields["storage_class"] = "ticket_attachment"
            fields["record_type"] = "SUPPORT_ATTACHMENT"
        out.append(RawRecord(
            evidence_id=ef.file_id,
            captured_at=ef.captured_at,
            resource_id=rid,
            fields=fields,
            observed_at=parse_ts(str(item.get("observed_at") or "")) or ef.captured_at,
            system_hint=item.get("system") or system_for(rid),
            location="visual",
            collection=str(fields.get("collection") or ""),
            source_format="visual",
        ))
    return out


def file_digest(ef: EvidenceFile) -> str:
    return hashlib.sha256(ef.path.read_bytes()).hexdigest()


def files_prompt_for(ef: EvidenceFile) -> str:
    template = (PROMPTS_DIR / "extract_files.md").read_text(encoding="utf-8")
    return (template.replace("{{file_name}}", ef.path.name).replace("{{origin}}", ef.origin)
            .replace("{{captured_at}}", ef.captured_at.isoformat().replace("+00:00", "Z")))


def file_records(ef: EvidenceFile, payload: dict) -> list[RawRecord]:
    """Files listed by name only; `file:<name>` is resolved to a resource id through data-catalog links."""
    out = []
    for item in (payload or {}).get("files", []):
        name = str(item.get("file") or "").strip()
        if not name:
            continue
        fields = {"file": name, "result": item.get("result") or "FOUND", "note": item.get("note")}
        out.append(RawRecord(ef.file_id, ef.captured_at, f"file:{name}", fields,
                             parse_ts(str(item.get("observed_at") or "")) or ef.captured_at,
                             "object_storage", "visual", "file_listing", "visual"))
    return out


def extract(ef: EvidenceFile, llm, known_files=()) -> tuple[list[RawRecord] | None, set, bool]:
    """(records, coverage, complete). records is None (not []) when the artifact could not be read at all: its
    contents are unknown, not empty. complete=False means only an OCR fallback read it (findings only)."""
    payload = None
    if not vision_llm():
        log.info("GDA_VISION=0: vision model not used for %s", ef.file_id)
    elif llm is None:
        log.warning("no LLM adapter for visual evidence %s", ef.file_id)
    else:
        result = llm.complete(task="extract_visual", prompt=prompt_for(ef), images=[ef.path], json_schema=SCHEMA)
        payload = result.parsed_json if result else None
    if not isinstance(payload, dict):
        text = ocr.ocr_text(ef.path) if vision_ocr_fallback() else None
        if text and text.strip():
            records = ocr.fallback_records(ef, text, known_files)
            log.warning("visual extraction unavailable for %s: %d record(s) from the OCR fallback", ef.file_id, len(records))
            return records, set(), False
        log.warning("visual extraction unavailable for %s", ef.file_id)
        return None, set(), False
    records = records_from_payload(ef, payload)
    if vision_grounding():
        records = ocr.GROUNDING.check(ef, records, ocr.ocr_text(ef.path))
    if not records:
        # no resource ids printed: the artifact may list stored files by name (second, cheaper pass)
        listing = llm.complete(task="extract_files", prompt=files_prompt_for(ef), images=[ef.path], json_schema={"type": "object"})
        if listing and isinstance(listing.parsed_json, dict):
            records = file_records(ef, listing.parsed_json)
            if vision_grounding():
                records = ocr.GROUNDING.check(ef, records, ocr.ocr_text(ef.path))
        elif ocr.GROUNDING.files.get(ef.file_id, {}).get("dropped") and vision_ocr_fallback():
            # everything the model returned was ungrounded and no listing pass is available: read it by OCR
            records = ocr.fallback_records(ef, ocr.ocr_text(ef.path) or "", known_files)
            log.warning("%s: vision records ungrounded; %d record(s) from the OCR fallback", ef.file_id, len(records))
            return records, set(), False
    return records, set(), True


def prefetch(manifest: list[EvidenceFile], llm, workers: int = 4) -> None:
    """Warm the cache for every visual file in parallel (later sequential calls are cache hits)."""
    from concurrent.futures import ThreadPoolExecutor

    visual = [ef for ef in sorted(manifest, key=lambda e: e.file_id)
              if ef.path.suffix.lower() in VISUAL_SUFFIXES and ef.path.exists()]
    if llm is None or not visual or not vision_llm():
        return
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda ef: llm.complete(task="extract_visual", prompt=prompt_for(ef), images=[ef.path],
                                              json_schema=SCHEMA), visual))


def render_markdown(entries: list[tuple[EvidenceFile, dict]]) -> str:
    """Human-auditable dump of what the model read from each visual artifact."""
    lines = ["# Extracted visual evidence", "",
             "Generated from the cached `extract_visual` LLM results. One section per PNG/PDF file.", ""]
    for ef, payload in entries:
        lines.append(f"## {ef.file_id} — `{ef.path.name}` (captured {ef.captured_at.isoformat()})")
        lines.append("")
        recs = (payload or {}).get("records", [])
        if not recs:
            lines.append("_no records extracted_")
        for r in recs:
            lines.append(f"- `{r.get('resource_id')}` ({r.get('system') or system_for(str(r.get('resource_id')))}): "
                         + json.dumps(r.get("fields", {}), ensure_ascii=False, sort_keys=True))
        lines.append("")
    return "\n".join(lines)
