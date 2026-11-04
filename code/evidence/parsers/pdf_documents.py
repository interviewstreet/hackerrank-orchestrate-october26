"""Parser for PDF business documents (selectable text, extracted with pypdf).

Documents are matched by content, not file name:

* Register rows ``ORD-… | user_… | … | Retain until …`` become one
  LEGAL_HOLD_RECORD observation per row (each row is a different subject).
* Every platform resource id in the text (``support_001``, ``audit_record_003``)
  becomes an observation of that resource.
* A document with no resource id becomes one observation keyed by its own
  reference number (statement / journal reference), system = manifest origin.

Document-level identifiers (emails, phones, user ids) are attached to each
observation only when the document concerns a single subject, so multi-person
documents cannot cross-link people.
"""

from __future__ import annotations

import re

from ..models import PRESENT, ParseIssue
from ..normalize import (
    PHONE_RE,
    default_category_for_resource,
    extract_emails,
    extract_phones,
    extract_resource_ids,
    extract_user_ids,
    system_for_resource,
)
from .common import ParseResult, make_record

FMT = "pdf"
REGISTER_ROW_RE = re.compile(
    r"(?P<order>ORD-\d+)\s*\|\s*(?P<user>user_\d+)\s*\|(?P<rest>[^\n]*?Retain until\s+(?P<until>[^|\n]+?))\s*(?:\||$)",
    re.I | re.M,
)
DOC_REF_RE = re.compile(r"\b(?:Statement|Reference|reference)\s+([A-Z]{2,5}-[\w-]+)")
TICKET_RE = re.compile(r"\bCS-\d+\b")
ORDER_RE = re.compile(r"\bORD-\d+\b")


def extract_pdf_text(path) -> list[str]:
    from pypdf import PdfReader  # imported lazily so other formats work without it

    reader = PdfReader(str(path))
    return [(p.extract_text() or "") for p in reader.pages]


def parse_pdf(ev) -> ParseResult:
    res = ParseResult()
    try:
        pages = extract_pdf_text(ev.absolute_path)
    except ImportError:
        res.issues.append(ParseIssue(ev.file_id, "error", "pypdf is not installed; PDF skipped"))
        return res
    except Exception as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"PDF text extraction failed: {exc}"))
        return res
    text = "\n".join(pages)
    if not text.strip():
        res.issues.append(ParseIssue(ev.file_id, "unsupported", "PDF has no extractable text (image-only?)"))
        return res
    res.bump("pages", len(pages))

    common_raw = {"document_text": text, "tickets": TICKET_RE.findall(text), "orders": ORDER_RE.findall(text)}

    # 1. Register rows (multi-subject documents).
    register_spans = []
    for m in REGISTER_ROW_RE.finditer(text):
        register_spans.append(m.span())
        row = m.group(0)
        payload = {
            "order_reference": m.group("order"),
            "subject_reference": m.group("user"),
            "retained_until": m.group("until").strip(),
            "row_text": row.strip(),
        }
        res.records.append(make_record(
            ev, system_id="legal_service", resource_id=m.group("order"), observed_at=ev.captured_at,
            presence=PRESENT, payload=payload, claim_only=False, source_format=FMT,
            locator=f"register row {len(register_spans)}", data_category="LEGAL_HOLD_RECORD",
            collection="legal_retention_register", raw_extra={"document_kind": "register"},
        ))
        res.bump("register_rows")

    # Text outside register rows decides the document's own subject.
    outside = text
    for a, b in reversed(register_spans):
        outside = outside[:a] + outside[b:]
    emails = extract_emails(outside)
    phones = extract_phones(outside)
    users = extract_user_ids(outside)
    rids = extract_resource_ids(outside)
    single_subject = len(emails) <= 1 and len(users) <= 1 and len(phones) <= 1
    doc_terms = set()
    pii = {}
    if single_subject:
        doc_terms |= {("email", e) for e in emails} | {("phone", p) for p in phones} | {("user_id", u) for u in users}
        if emails:
            pii["email"] = emails[0]
        if phones:
            raw_phone = PHONE_RE.search(outside)
            pii["phone"] = raw_phone.group(0) if raw_phone else phones[0]
    elif emails or phones or users:
        res.issues.append(ParseIssue(ev.file_id, "warning", "multiple subjects in document; identifiers not cross-linked"))

    is_attachment = "attachment" in text.lower()
    for rid in rids:
        category = default_category_for_resource(rid)
        if category is None and rid.startswith("support_"):
            category = "SUPPORT_ATTACHMENT" if is_attachment else "SUPPORT_MESSAGE"
        payload = {"resource_id": rid}
        if single_subject and users:
            payload["subject_reference"] = users[0]
        res.records.append(make_record(
            ev, system_id=system_for_resource(rid) or ev.origin, resource_id=rid, observed_at=ev.captured_at,
            presence=PRESENT, payload=payload, claim_only=False, source_format=FMT, locator="document",
            data_category=category, raw_extra=common_raw | {"document_kind": "resource_document"},
            extra_terms=doc_terms, pii_override=dict(pii),
        ))
        res.bump("resource_mentions")

    if not rids and not register_spans:
        ref = DOC_REF_RE.search(text)
        doc_id = ref.group(1) if ref else ev.absolute_path.stem
        payload = {"document_reference": doc_id}
        if single_subject and users:
            payload["subject_reference"] = users[0]
        res.records.append(make_record(
            ev, system_id=ev.origin, resource_id=doc_id, observed_at=ev.captured_at, presence=PRESENT,
            payload=payload, claim_only=False, source_format=FMT, locator="document",
            raw_extra=common_raw | {"document_kind": "business_document"}, extra_terms=doc_terms,
            pii_override=dict(pii),
        ))
        res.bump("documents")
    return res
