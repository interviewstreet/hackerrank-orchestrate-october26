"""PDF text extraction (pdftotext, page-aware) and shared text->observation logic for PDFs and OCR'd images."""
from __future__ import annotations

import re
import subprocess
from typing import Dict, List, Tuple

from ..contracts import Coverage, Observation
from ..util import RESOURCE_ID_RE, category_for_resource, extract_identifiers


def pdf_pages(path: str) -> List[str]:
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=False).stdout
    return [p for p in out.split("\f") if p.strip()]


def text_to_observations(evidence_id: str, captured_at: str, pages: List[str], fmt: str, confidence: float,
                         file_label: str) -> List[Observation]:
    """One observation per resource id mentioned on a page; identifiers come from the same page."""
    obs: List[Observation] = []
    seen = set()
    whole = file_label + " " + " ".join(pages)           # an attachment is described on a later page / by its name
    for pno, text in enumerate(pages, 1):
        ids = extract_identifiers({"text": text})
        rids = list(dict.fromkeys(RESOURCE_ID_RE.findall(text)))
        for rid in rids:
            if rid in seen:
                continue
            seen.add(rid)
            system, cat = category_for_resource(rid)
            if rid.startswith("support_") and re.search(r"attachment", whole, re.IGNORECASE):
                cat = "SUPPORT_ATTACHMENT"
            obs.append(Observation(
                evidence_id=evidence_id, captured_at=captured_at, system_id=system or "", resource_id=rid,
                data_category=cat or "", state="PRESENT", observed_at=captured_at, emails=ids["emails"],
                user_refs=ids["user_refs"], hashes=ids["hashes"], phones=ids["phones"], names=[],
                attrs={"page": pno, "file": file_label, "text_excerpt": " ".join(text.split())[:300]},
                source_format=fmt, locator=f"page {pno}", confidence=confidence))
    return obs


def parse_pdf(evidence_id: str, captured_at: str, path: str) -> Tuple[List[Observation], List[Coverage]]:
    pages = pdf_pages(path)
    return text_to_observations(evidence_id, captured_at, pages, "pdf", 1.0, path.split("/")[-1]), []
