# Vision evidence: spec and model options (WP-7)

Status: **implemented** (steps 1–3, see §10), 2026-10-25. Decisions in §9. Deadline 2026-10-25 12:30 UTC. Scope: the PNG/PDF evidence path and
the edge cases `case_e14` and `case_e15` (`code/evaluation/edge_dataset/`).

## 1. Problem

`case_e14` (an export that only a screenshot shows) and `case_e15` (a file listed by name in a storage
browser and linked to `object_N` by a data-catalog activity) fail in the edge eval. The system already has
a VLM, so the cause is not a missing model:

| Layer | Today |
|---|---|
| Extraction | `evidence/multimodal.py`: `extract_visual` (records with resource ids), then `extract_files` (file-name listing) when the first pass finds no ids. Model alias `vision` = `claude-sonnet-5-5`. |
| Cache | `code/cache/llm_cache.jsonl`, key = task + alias + prompt + sha256(image). 15 real images are cached (19 entries). |
| Edge runner | `edge_cases.py run` defaults to `--backend offline`, which **ignores the cache and skips images**. |
| Result | The 3 edge PNGs have never been read by any model, so e14/e15 can't pass. Whether the VLM reads them correctly is untested. |

There are two separate gaps:

1. **Coverage:** the edge PNGs have no cached extraction, so the replay/offline gate can't exercise them.
2. **Robustness:** without a key or network, a new image is skipped silently. Nothing checks that the
   VLM's transcription is faithful, so a misread email or a hallucinated resource id would go unnoticed.

## 2. Goals and non-goals

Goals
- G1: e14 and e15 pass in the default (replay) edge run, with no network.
- G2: the quality gate stays 10/10 and `output.csv` stays byte-identical. The 19 real cache entries must not
  be invalidated, so **no edits to `prompts/extract_visual.md` or `prompts/extract_files.md`**: changing a
  prompt changes every cache key and forces a paid re-warm of about $1.31.
- G3: a check that what the VLM returns actually appears in the image (hallucination guard).
- G4: live spend for this work ≤ $0.30 (cap $3.00, $1.44 spent so far).

Non-goals
- Replacing the main VLM for the real 15 images before the deadline.
- Running a local VLM on this VM (4 CPU, 7 GB RAM, no GPU): see §3.3.

## 3. Options

Unit costs come from `llm/pricing.py`, USD per million input/output tokens:
Haiku 5.5 0.10/0.50, Sonnet 5.5 2.00/10.00, Opus 5.5 4.00/20.00. Measured: the 19 Sonnet calls through
`claude -p` cost $1.31, about $0.069 per image. Roughly 45k of the input tokens per call are the CLI's own
system prompt, not the image.

### 3.1 Cloud VLMs (all fit the existing `LLMAdapter`; choose with `GDA_MODEL_VISION`)

| Option | Backend | Est. cost per image | Strengths | Weaknesses |
|---|---|---|---|---|
| **A. Claude Sonnet 5.5** (current) | `claude_cli` or `anthropic` | ~$0.07 via CLI; ~$0.01 via API (≈2–3k tokens) | Already produced the 19 cached real extractions; strong on tables, screenshots and PDFs; JSON schema already tuned | CLI overhead makes each call cost 5–10× more than the API |
| **B. Claude Haiku 5.5** | same | ~20× cheaper than Sonnet | Very cheap; good enough for clean console screenshots | Weaker on dense PDFs and small fonts; would need an agreement check against Sonnet before trusting it |
| **C. Claude Opus 5.5** | same | ~2× Sonnet | Best accuracy for hard pages | Not needed for clean screenshots; use only to settle disagreements |
| **D. Another vendor's VLM** (e.g. an OpenAI GPT vision model) | `openai` (exists, needs `GDA_PRICE_OVERRIDE_VISION`) | depends on vendor | An independent second opinion, so errors are less likely to coincide | Second key and vendor; no cached results; output format untested |

### 3.2 Local deterministic OCR (no model weights, CPU only)

| Option | Install | Strengths | Weaknesses |
|---|---|---|---|
| **E. Tesseract 5** + `pytesseract` | `apt install tesseract-ocr` (needs sudo) | Deterministic, offline, fast on CPU, good on rendered UI text | Gives text only: needs a small rule-based parser to turn rows into records; weaker on Cyrillic without `tesseract-ocr-rus` |
| **F. RapidOCR** (PaddleOCR models on ONNX Runtime) | `pip install rapidocr_onnxruntime` (about 50 MB) | No sudo; strong on screenshots; multilingual models | Text only, same parser needed; an extra dependency in `code.zip` requirements |

### 3.3 Local VLMs (assessed and rejected for now)

Small open VLMs, for example the Qwen2.5-VL 3B/7B family, Florence-2 (OCR-oriented, under 1B) or
SmolVLM, would be a fully offline structured extractor. On this VM (no GPU, 7 GB RAM) a 3B model at 4-bit
runs at roughly a minute per image or worse, adds a large dependency (llama.cpp/ollama or torch) and isn't
deterministic across builds. That's not worth it before the deadline. Revisit if evaluation must run
air-gapped and at volume.

### 3.4 Ollama on the host (added 2026-10-24 after the owner offered GPU/NPU via Ollama)

Probe from the VM: Ollama 0.34.2 answers at `http://10.0.2.2:11434` (the VirtualBox NAT gateway, i.e. the host).
Installed: `qwen3:8b` and `qwen3-coder-next:latest` (local, text only) and two `:cloud` models, which run on
ollama.com, so their prompts and images leave the machine. **No local vision model is installed yet.**
Candidates from the Ollama library: `qwen2.5vl:7b` (strong on documents and screenshots), `gemma3:12b`,
`llama3.2-vision:11b`, `minicpm-v`. Check tags and sizes against the library before pulling. As far as we know,
Ollama uses the GPU (CUDA/ROCm/Metal) or CPU; don't count on the NPU.

How the judge is likely to check this, and what follows from it:
- The graded artifact is `output.csv`. `code.zip` must run from a clean clone with the README, in an
  environment we don't control, which certainly won't have our host's Ollama at `10.0.2.2`.
- So Ollama, like `claude_cli` today, is a **development-time backend only**. The default `replay` backend
  serves every model result from the committed cache, so the judge's rerun is byte-identical with no
  network, no GPU and no key. If a judge does have Ollama, `GDA_LLM_BACKEND=ollama` must work as
  documented, and must degrade to "skip with a warning" when the server or model is missing.
- `usage_report.md` must list Ollama calls like any other model: provider `ollama (local)`, the exact model
  tag, call count and tokens (`prompt_eval_count` / `eval_count` from the API), cost $0 for local models.
  `:cloud` models are not local; don't use them for evidence extraction.

Design for an `ollama` backend (`llm/backends/ollama.py`, standard library `urllib` only, no new dependency):
- `POST {OLLAMA_HOST}/api/chat` with `images: [base64]`, `format: <JSON schema>`, `stream: false`,
  `options: {temperature: 0, seed: 7}`. `OLLAMA_HOST` defaults to `http://127.0.0.1:11434`.
- Model via `GDA_MODEL_VISION=qwen2.5vl:7b` and price via `GDA_PRICE_OVERRIDE_VISION="0,0"`.
- **Cache key:** today the key uses the alias (`vision`), not the model, so an Ollama result for a real
  image would be indistinguishable from the committed Sonnet entry. For non-Anthropic backends, add
  `backend:model` to the key; Anthropic keys stay unchanged, so the 61 existing lines remain valid.

Where a local VLM fits in the plan:
- Step 1 alternative: warm the 3 edge images with the local VLM ($0) instead of Sonnet (~$0.25). Then
  the edge cache is from a different model than the real cache; record that in the usage report.
- Step 2 alternative: use the local VLM as the **second opinion** in the grounding check (it agrees with
  Sonnet on ids/emails/files) instead of OCR. This is stronger than OCR on layout but not deterministic
  across Ollama versions, so cache its results too.
- Step 3: a local VLM is a better offline fallback than OCR-only parsing, for anyone who has Ollama.

## 4. Recommendation

Do it in three steps; each can be stopped after.

**Step 1 (needed for G1, ~$0.25). Warm the edge images with the current VLM and make the edge runner use replay.**
- Change the `edge_cases.py run` default backend from `offline` to `replay`. Replay reads the cache and
  falls back to the heuristic otherwise, so intent behaviour is unchanged for uncached texts.
- Run `GDA_LLM_BACKEND=claude_cli python3 code/evaluation/edge_cases.py run --backend claude_cli` once.
  That's 3 `extract_visual` calls plus at most 1 `extract_files` call for the e15 listing, and intent
  batches for the new request texts (Haiku, under $0.01). Commit the new cache lines.
- The edge PNGs are rendered deterministically (Pillow default font, fixed layout), so their bytes and
  cache keys are stable across rebuilds. Add a test asserting the PNG sha256, so a Pillow upgrade can't
  silently orphan the cache.
- If e15 still fails after warming, the fault is in name→resource linking (`file_aliases` /
  `object_storage` category), not in vision. Fix it in deterministic code with a unit test.

**Step 2 (G3, $0). OCR cross-check as a hallucination guard (option F, or E if sudo is available).**
- New `evidence/ocr.py` with an optional dependency, imported lazily. If it's missing, the guard is skipped
  with one info-level log line.
- For every VLM record, check that its `resource_id`, `email`, `phone` and `file` values occur in the OCR
  text of the same image, after normalisation (case-fold; strip spaces in phones). A record whose id isn't
  found is dropped and logged; an identifier that isn't found is removed from the record.
- Run it in `check_all.py` as a new invariant `visual_grounding` over all 18 images (15 real + 3 edge).
  Report the agreement rate in `evaluation_report.md`.

**Step 3 (optional, robustness). OCR-only fallback when no VLM result exists.**
- On a cache miss with no live backend, run OCR plus a simple row parser (one record per line containing a
  `prefix_N` id or a file name, with any emails, phones and status words on that line) instead of skipping
  the image.
- Label these records `source_format="ocr"` so they're auditable. Use them only for findings, never to
  prove absence: a missing OCR word must not turn into a COMPLETE.

**Model choice:** keep **Sonnet 5.5** as the `vision` model, since its 19 real extractions are what
`output.csv` rests on. Don't switch to Haiku for the submission. A Haiku-vs-Sonnet agreement study over the
18 images costs about $0.05 and could justify Haiku later. Opus is only worth it as a tie-breaker. For
future live runs, prefer the `anthropic` API backend over `claude_cli` for vision: it's the same model at
about a seventh of the cost per image, because there's no CLI system prompt.

## 5. Acceptance criteria

1. `python3 code/evaluation/edge_cases.py run` (replay, offline-safe): e14 and e15 PASS; gate failures 0.
2. `python3 code/evaluation/check_all.py`: all checks pass (11/11 with `visual_grounding` after step 2),
   and `output.csv` is byte-identical.
3. No change to `prompts/*.md`; the existing 61 cache lines are unchanged (append-only).
4. Live spend recorded in `code/cache/ledger/` ≤ $0.30 for this work package.
5. `usage_report.md` and `evaluation_report.md` §3 updated with the edge results and the extra calls.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Prompt or schema edits invalidate the 19 real cache entries | G2: prompts frozen; any change needs an explicit re-warm decision |
| Pillow version changes the PNG bytes, so edge cache misses | sha256 test (step 1); PNGs are committed, and the build reuses them if the bytes match |
| OCR false negatives drop true VLM records (step 2) | Drop only ids that are missing from OCR; keep the record if OCR returned nothing at all (unreadable image) |
| VLM nondeterminism if re-warmed | The cache is the source of truth; re-warm only on purpose, then rerun the gate |
| A new dependency breaks a clean install | OCR is optional and lazily imported; README documents `pip install rapidocr_onnxruntime` as extra |

## 7. Open questions for the owner

0. Pull a local vision model on the host (`ollama pull qwen2.5vl:7b` suggested), so the `ollama` backend
   (§3.4) can be built and measured against Sonnet on the 18 images?
1. Approve about $0.25 of live spend for step 1, via the `claude_cli` subscription or the `anthropic` API,
   or warm with the local VLM instead ($0)?
2. Step 2 OCR engine: RapidOCR (pip, no sudo) or Tesseract (apt)?
3. Do step 3 before the deadline, or leave it as documented future work?

## 8. Results: `ollama` backend with `qwen2.5vl:7b` (2026-10-24)

Implemented: `llm/backends/ollama.py` (standard library only, temperature 0, seed 7, PNG/JPG only).
Results are cached under a `backend:model` variant key with a `base` pointer; replay serves the default
(Sonnet) entry first and a variant only when no default exists. `code/evaluation/vision_compare.py` writes
`code/evaluation/vision_comparison.md`.

- 14 images, 6 min 48 s on the host GPU (~8–30 s per image), $0.
- Against Sonnet on the 11 real PNGs: id recall 84.6%, **precision 55.0%**, field agreement on common ids 91.7%.
- Every contested item checked by eye in the screenshots (`account_5762`, `support_1034`, `marketing_001`
  and its email) supports Sonnet. Qwen's typical failure: it **copies the prompt's example ids**
  (`support_001…008`, `export_001/002`, `analytics_N`) when an artifact prints no matching id, and misreads
  `account_5762` as `search_5762`.
- Edge: e14 and e16 correct. On e15 Qwen invented `export_001/002` for the storage browser, so the file-listing
  pass never ran and e15 still fails.
- Real pipeline unaffected: cache append-only (61 → 75 lines), gate 10/10, `output.csv` byte-identical.

Conclusion: `qwen2.5vl:7b` is **not reliable enough** to be the primary extractor or the grounding judge for
real evidence. It's useful as a free, offline second opinion and for simple screenshots. Options for e15:
warm that one image with Sonnet (~$0.07), or try a larger local VLM if host VRAM allows.

## 9. Decisions (owner, 2026-10-24)

- **Ollama support is committed** as an optional, development-time backend. The judge-facing default stays
  `replay`, which reproduces `output.csv` with no network, GPU or key. Sonnet stays the vision model for real evidence.
- The edge runner now defaults to `replay`, so committed transcriptions (including the Qwen ones for the
  edge screenshots) are used. e14 and e16 pass.
- **case_e15 is a documented known limitation.** The only cached transcription of its storage-browser
  screenshot comes from `qwen2.5vl:7b`, which invented `export_001/002` instead of listing the file, so the
  file-name pass (`extract_files`) never runs and the file is not linked to `object_8151`. The case keeps its
  hand-written expected answer and is labelled `known-limitation` (not gated). It would pass with a Sonnet
  transcription (~$0.07) or a stronger local VLM. Steps 2–3 (OCR grounding, OCR fallback) are future work.

## 10. Implementation (2026-10-25)

Owner decisions: OCR engine **Tesseract** (apt), Sonnet warm-up for e15 approved, both guards **switchable and on
by default**, `ollama` a full `GDA_LLM_BACKEND` provider.

| Step | Implemented as | Switch |
|---|---|---|
| 1. Coverage | e15's storage-browser screenshot transcribed by Sonnet through `claude_cli`: `extract_visual` (no ids) + `extract_files` (2 files). **$0.147** (two calls, more than the $0.07 estimate; WP total $0.147 ≤ $0.30). Cache append-only (43 → 45 lines). e15 relabelled `needs-vision` and passes. | – |
| 2. Grounding guard | `evidence/ocr.py` `Grounding.check`: each vision record's id (or listed file name) must occur in the OCR text of its image; emails/phones that do not occur are removed from the record. Matching is tolerant of OCR slips: NFKC + casefold, Cyrillic look-alikes mapped to Latin (`Баскир_9288` → `backup_9288`), separators ignored, ≤1 edit (<12 chars) or ≤2 edits, phones by digit run. No OCR text → nothing dropped. Invariant `visual_grounding` in `check_all.py` (11/11). | `GDA_VISION_GROUNDING` (default 1) |
| 3. OCR fallback | No vision result (cache miss, offline), or every vision record ungrounded with no listing pass: one record per OCR line with a known-prefix id (≥3 digits) or a file name the data catalog links (fuzzy), with the line's email/phone/status. `source_format="ocr"`; such records can only be PRESENT / ACTIVE / RETAINED / LINK, and the file still counts as unread, so no COMPLETE rests on it (exit 4 stays). | `GDA_VISION_OCR_FALLBACK` (default 1) |

OCR text comes from `pdftotext` (PDF text layer), else `pdftoppm` + `tesseract -l eng+rus`. It is cached by file
sha256 in `code/cache/ocr_cache.jsonl` (18 files), so replay runs (and the judge's) reproduce the guard without the
tools; a unit test fails if an image's bytes drift from its cached OCR.

Results:
- Real evidence: **34/34** Sonnet records grounded (first pass 33/34; the 3 misses were OCR slips, fixed by the
  tolerant matching, not VLM errors). `output.csv` byte-identical, with either switch on or off.
- Edge: the guard drops Qwen's invented `export_001/002` on e15; with only the Qwen transcription, the OCR fallback
  still links `account_export_15.zip` → `object_8151` and e15 passes at $0. Gate failures 0.
- Offline (no LLM): the OCR fallback recovers 3 of the 8 findings that otherwise flip to COMPLETE; the other 5 stay
  flagged by exit 4.
- `ollama` provider: defaults `qwen3:8b` (intent) and `qwen2.5vl:7b` (vision), JSON mode, `think: false`, PDFs as
  page images via `pdftoppm`. Live check against the host: intent 3/3 (incl. a Russian "do not delete"), one PNG
  and one PDF read in 15 s / 31 s, $0. The guard dropped Qwen's invented `account_18` on the PDF; Qwen also reported
  `user_11` instead of `account_5762` on the admin console. Same conclusion as §8: fine for intent and as a free
  second opinion, not as the primary extractor.
