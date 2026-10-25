"""PDF evidence: extract the text layer, then key facts (ids, emails, users).

Implemented with pdfplumber when available, falling back to pypdf. The four
supplied PDFs are single-subject business artifacts; we emit a fact for each
resource id named in the document, classified from document context.
"""
import re

from ..facts import EMAIL_RE, RESOURCE_RE, USER_RE

try:  # optional dependency, documented in requirements.txt
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    try:
        from PyPDF2 import PdfReader
    except Exception:
        PdfReader = None


def extract_pdf_text(path):
    if pdfplumber is not None:
        try:
            with pdfplumber.open(path) as pdf:
                return "\n".join((p.extract_text() or "") for p in pdf.pages)
        except Exception:
            pass
    if PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            return ""
    return ""


def facts_from_document_text(text, source_id, store, observed,
                             subject_only=False):
    """Shared by PDF and OCR text: emit facts for resources named in text."""
    if not text:
        return 0
    before = len(store.facts)
    low = text.lower()
    emails = {m.group(0).lower() for m in EMAIL_RE.finditer(text)}
    users = set(USER_RE.findall(text))
    if subject_only:  # screenshot: only the opened subject may link records
        emails = {next(iter([m.group(0).lower()
                             for m in EMAIL_RE.finditer(text)]))} if emails else set()
        found_users = USER_RE.findall(text)
        users = {found_users[0]} if found_users else set()
    resources = sorted(set(RESOURCE_RE.findall(text)))  # prefix only groups
    # RESOURCE_RE returns the prefix group; recover full ids separately.
    full_ids = sorted(set(re.findall(
        r"\b(?:account|search|analytics|support|export|data_flow|backup|"
        r"audit_record|tombstone|legal_hold|marketing|cache|email_delivery|"
        r"object)_[\w\-]+\b", text)))
    for resource_id in full_ids:
        prefix = resource_id.split("_")[0]
        if resource_id.startswith("support_"):
            category = "SUPPORT_ATTACHMENT" if "attachment" in low \
                or "delivery" in low else "SUPPORT_MESSAGE"
            system = "support_platform"
        elif resource_id.startswith("audit_record"):
            category, system = "SECURITY_AUDIT_LOG", "security_service"
        elif resource_id.startswith("export_"):
            category, system = "USER_EXPORT", "export_service"
        elif resource_id.startswith("account"):
            category, system = "USER_PROFILE", "account_service"
        else:
            continue
        store.add(source_id, "evidence", observed, system, resource_id,
                  category, "PRESENT",
                  record={"email": next(iter(emails), None)} if emails else None,
                  emails=emails or None, user_ids=users or None,
                  exposed=bool(emails), attributable=bool(emails or users))
    return len(store.facts) - before


def parse_pdf_file(path, source_id, store, manifest_ts):
    return facts_from_document_text(extract_pdf_text(path), source_id, store,
                                    manifest_ts)
