# Ghost Data Still Exists solution

## Run

From the repository root with Python 3.10 or newer:

```sh
python code/main.py
```

The program reads `dataset/`, parses the participant-facing JSON and SQL snapshots, service exports, and text logs, matches current and historical identifiers, applies timestamp cutoffs, writes root `output.csv`, and validates schema, row count, ordering, JSON syntax, and step numbering. It uses only the Python standard library. Run from any current directory; paths are resolved relative to this file.

## Evidence and limits

Workflow statuses are ignored. Identity matching uses the request address, current identity snapshot, and email/name/phone/hash changes in the audit history. Evidence captured after `audit_at` is excluded. Structured evidence is associated via identifiers and resource IDs; SQL is read in an in-memory SQLite database. Policy-compliant security records, redacted tombstones/support records, anonymous analytics, disabled integrations, and blocked backups are represented separately from records that must be deleted.

This deadline implementation does not perform OCR on screenshots; PDF text extraction supports simple embedded text streams, does not fully reconstruct every cross-system event dependency, and its sample evaluation is below production-grade. Treat the generated output as a deterministic evidence-based baseline requiring review, not as hidden-test-validated. It does not call an LLM; usage is zero model tokens and zero model cost.
