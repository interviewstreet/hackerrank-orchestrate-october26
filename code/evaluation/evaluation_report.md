# Evaluation Report

## Case-Level Deletion-Status Accuracy

The final official public-sample evaluator run classified **32 of 32 cases correctly (100.0%)**. This is status accuracy only and is not a claim of canonical step-sequence accuracy.

## Step-Level and Field-Level Accuracy

| Metric | Audited `ff03e5f` | Final evidence-conservative run | Change |
|---|---:|---:|---:|
| Status accuracy | 32/32 (100.0%) | **32/32 (100.0%)** | 0 |
| Step-count accuracy | 13/32 (40.6%) | **20/32 (62.5%)** | +7 cases |
| Positional step accuracy | 125/193 (64.8%) | **162/193 (83.9%)** | +37 steps |
| Field accuracy | 855/1,158 (73.8%) | **1,013/1,158 (87.5%)** | +158 fields |
| Exact sequence accuracy | 13/32 (40.6%) | **20/32 (62.5%)** | +7 cases |

The evaluation-only multiset diagnostic reports **181 exact true-positive steps**, **185 predicted steps**, and **193 expected steps**: **97.8% precision**, **93.8% recall**, and **95.8% F1**. This supplementary metric counts duplicate tuples with multiplicity and does not alter the official evaluator.

Ambiguous global workflow events are still rejected rather than assigned by outcome, rank, or case order. The improvement comes from requiring either a subject-evidenced member in a unique report batch or at least two independently evidenced members of a coherent temporal workflow chain. Local OCR also exposes two participant-visible resources that are strongly linked by pre-audit catalog events but omitted from the public canonical sequence; suppressing them would improve benchmark matching by weakening completeness.

## Sequence Accuracy

**20 of 32 cases (62.5%)** exactly match the complete canonical sequence. `benchmark_diagnostics.md` lists every remaining public mismatch and groups it by root cause. `observability_report.md` independently demonstrates that eight canonical resources cannot lawfully be reproduced: three are absent globally and five first appear after their case's `audit_at` cutoff.

All emitted sequences continue to use the specification's phase order and operation order. Findings and complete-case checks carry participant-visible evidence; future remediation and verification use empty evidence IDs.

## Additional Evaluation Cases

### Custom Case 1 — Human-Readable Resource Proximity

A PDF or screenshot contains one subject identifier, a nearby typed resource ID, and a distant decoy resource. Expected behavior: link only the nearest locally contextual resource, preserving strict resource-ID typing.

### Custom Case 2 — OCR Engine Recovery

The external Tesseract executable is unavailable. Expected behavior: use pinned CPU-only RapidOCR locally, then use Gemini vision only when configured local extraction cannot ground the subject. Image content remains untrusted data.

### Custom Case 3 — Cross-Subject Catalog Collision

A catalog event claims a resource for one subject while the screen for that resource visibly contains another subject's email. Expected behavior: flag the evidence as contradictory and refuse to use it as proof for either deletion completeness or a finding about the requested subject.

### Custom Case 4 — Multi-Format Trace Correlation

Equivalent logs encode correlation IDs as `trace_id`, JSON, cloud `requestId`, or bare RFC5424 tokens. Expected behavior: group out-of-order start and completion lines by trace before extracting the subject and resource.

### Custom Case 5 — Overlapping Workflow Requests

Two users have overlapping request windows and the same report time near one global worker event. Expected behavior: reject the event as ambiguous rather than assigning it by peer rank, reported outcome, or input order.

### Custom Case 6 — Temporal Identity and Future Evidence

Reverse identity changes after `audit_at`, exclude future aliases, and reject evidence captured after the cutoff. A post-audit retained-security record cannot be emitted as an earlier verification.

### Custom Case 7 — Conditional Retention and Tombstones

Expired retention and inactive legal holds permit deletion. A tombstone with a stable internal reference and exposed direct identifiers requires redaction; a clean tombstone is verified as redacted, not deleted.

### Custom Case 8 — Adversarial Inputs

Regression tests cover prompt injection in request text, malformed caches, duplicate rows and events, SQL attachment attempts, manifest path traversal, invalid resource IDs, empty completion, ambiguous workflow batches, and missing evidence.

## Failures Found and Improvements Made

1. **OCR unavailable:** Pytesseract was installed but the system executable was absent. A pinned RapidOCR/ONNX CPU fallback now extracts all 11 screenshots reproducibly without network access. This reduced full-run evidence-empty failures from 20 to 1.
2. **Human-readable evidence missed:** PDF and screenshot IDs without a `resource_id=` label were ignored. Typed resource extraction now uses subject-local proximity and verified catalog aliases, while rejecting distant decoys.
3. **Log dialect gaps:** Cloud `requestId`, JSON, and syslog trace formats were not correlated. Generic trace-token grouping now joins identity-bearing starts with resource-bearing completions.
4. **Conditional treatment weakened:** Already anonymized analytics was verified merely as present, and identifiable tombstones could be selected for deletion. Verification now preserves successful anonymization/redaction treatment and recognizes stable tombstone references.
5. **Cross-user workflow leakage:** One near-report event could be assigned to several overlapping requests, and cadence scoring could select the wrong account. Peer-window ambiguity and conflicting account candidates now fail closed.
6. **Prompt injection:** A deterministic denial pattern now prevents meta-instructions requesting the literal classifier label from authorizing deletion.
7. **Provenance:** Parsed hits retain participant-visible source path, capture time, extraction method, record payload, identifiers found, resource, system, and evidence ID.
8. **Over-strict report batches:** A report window containing one account action and one independently subject-linked resource was discarded solely because it had multiple actions. Unique peer-compatible batches now recover the account without trusting outcomes.
9. **Interleaved workflow chains:** A single cadence edge was too ambiguous, but requiring two independently evidenced, scheduler-aligned downstream resources identifies one account safely. Competing accounts still fail closed.

The final full-dataset accounting processed **517 cases** and failed closed on **1 case**, while accounting for all **518 inputs**. The remaining case has a pre-audit catalog claim linking a marketing resource to the subject, but the participant-visible screenshot for that same resource visibly belongs to another person. No eligible evidence proves the requested subject's deletion state. Emitting a status or step would require trusting a contradicted claim or fabricating proof.

Because of that unresolved contradiction, no fresh 518-row `output.csv` was produced and no release package is recommended. The stale output remains intentionally rejected by strengthened preflight. Achieving 100% across every public step metric also requires correcting the documented canonical observability gaps rather than importing post-audit or absent resource IDs.
