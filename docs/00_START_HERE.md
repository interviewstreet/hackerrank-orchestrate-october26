# 00 — START HERE (Beginner Guide)

Challenge: **Ghost Data Still Exists** (HackerRank Orchestrate, Oct 2026)
Goal: a program that reads 518 deletion requests and writes `output.csv` saying, for each one, whether the person's data is really gone, and the exact ordered steps to fix/prove it.

> **Deadline warning.** The challenge page says submission closes **Oct 26, 2026, 6:00 AM IST** and the AI-judge interview window follows submission. Check the live timer on the HackerRank page right now and plan backwards. Submit a *working* version early; improve after.

---

## 1. The idea in plain words

A customer says "delete me." A dashboard says "Complete." But copies still hide in a search index, a support ticket, an analytics table, a sync job, a backup. Your program is an **auditor**:

1. **Did they really ask for deletion?** (Some people only asked for an invoice copy, a correction, or to stop marketing mail → `NOT_APPLICABLE`, steps `[]`.)
2. **Who are they?** Find *all* their emails/phones/IDs, including old ones (`user_audit_log.csv`).
3. **What exists at `audit_at`?** Read the evidence files (SQL dumps, logs, JSON, PDFs, screenshots), ignoring anything captured after `audit_at`.
4. **What does policy require?** (`deletion_rules.csv`: DELETE / REDACT / ANONYMIZE / RETAIN.)
5. **Compare** "what exists" vs "what policy requires".
   - Everything correct → `COMPLETE` + verification steps with evidence IDs.
   - Anything wrong → `INCOMPLETE` + findings, then fixes, then re-checks.
6. **Write** one CSV row per case with an exact JSON step list.

## 2. The winning strategy (one paragraph)

**Do NOT let an LLM "decide" the audit.** The scoring compares exact step lists (system, resource, operation, evidence ID, order). Build a **deterministic Python engine** that parses evidence into structured facts and applies policy rules. Use an LLM only for two small, cheap jobs: (a) classify the multilingual `request_text` as deletion / non-deletion, (b) optionally read screenshots when OCR is not enough. Then **measure against `sample_output.csv`** (32 answered cases) and iterate until the engine matches all of them *by logic, not by hardcoding*. This is also what makes the token/cost report tiny and the AI interview easy.

## 3. What is in this playbook

| File | Use it for |
|---|---|
| `00_START_HERE.md` | This guide |
| `01_Problem_Analysis.md` | What I verified in the real data; corrections to the Gemini plan; hypotheses to test |
| `02_Architecture.md` | The design: modules, algorithms, ordering, edge cases |
| `03_Build_Prompts.md` | Copy-paste prompts for your AI coding tool, in order |
| `04_Evaluation_and_Report_Templates.md` | Evaluator spec + templates for `evaluation_report.md`, `usage_report.md`, `README.md` |
| `05_Submission_and_Interview.md` | Packaging, log.txt, final checklist, interview prep |

## 4. Setup (15 minutes, do this first)

You need: **Python 3.10+**, **git**, an **AI coding tool** (Claude Code, Codex CLI, Cursor, etc.), and optionally an LLM API key.

```bash
git clone https://github.com/interviewstreet/hackerrank-orchestrate-october26.git
cd hackerrank-orchestrate-october26
# put the dataset here so you have ./dataset/ (unzip dataset.zip at repo root)
python3 -m venv .venv            # Windows: py -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pandas pillow pytesseract pdfplumber
# OCR engine (needed for screenshots):
#   macOS:  brew install tesseract
#   Ubuntu: sudo apt install tesseract-ocr poppler-utils
#   Windows: install Tesseract from UB Mannheim build, add to PATH
```

Optional LLM key (never write it in code or in `log.txt`):
```bash
export ANTHROPIC_API_KEY="..."     # Windows PowerShell: $env:ANTHROPIC_API_KEY="..."
```

**Critical:** launch your AI coding tool **from the repo root** so it reads `AGENTS.md` and writes `log.txt` (that file is your required chat transcript). Keep `.venv` at the repo root, outside `code/`.

## 5. The 1-hour plan (be strict with the clock)

| Min | Step | Prompt (in `03_Build_Prompts.md`) | Done when |
|---|---|---|---|
| 0–10 | Setup, start tool at repo root, paste bootstrap prompt | P0 | Tool confirms it read AGENTS.md and logs a SESSION START |
| 10–15 | Explore data, write findings file | P1 | `code/evaluation/data_notes.md` exists |
| 15–25 | Loaders + identity resolver + intent classifier | P2, P3 | Every request maps to a user_id; 10-ish non-deletion cases flagged |
| 25–40 | Evidence parsers (SQL, JSON, logs, txt, PDF, PNG) → one `facts` table | P4 | Facts table has rows from all 5 formats |
| 40–50 | State at audit_at + policy engine + step builder + CSV writer | P5, P6 | `python3 code/main.py` writes 518 rows |
| 50–60 | Evaluator, compare to samples, fix top failures | P7 | Sample status 32/32; step F1 improving |
| After | Reports, README, package, submit | P8 | `05_Submission_and_Interview.md` checklist all ticked |

**If you are behind:** ship in this order of value: (1) valid 518-row file with correct statuses, (2) correct findings/remediation for common patterns, (3) evidence IDs and verification steps, (4) polish.

## 6. Beginner survival rules

1. **Run small, run often.** After every prompt, run the code and look at output for 3 cases before moving on.
2. **Never accept "it should work."** Ask the AI tool to run it and paste results.
3. **No hardcoding.** No case IDs, no resource IDs, no sample answers copied into code. The judge checks this and so will the hidden test.
4. **Time travel rule.** Anything dated after a case's `audit_at` must be ignored (evidence *and* activity rows).
5. **Commit often:** `git add -A && git commit -m "step X"` so you can roll back.
6. **Never commit secrets or `dataset/`.**
7. **Stuck >5 minutes?** Print the raw evidence for one failing case and compare with the expected sample steps by eye. Almost every bug is a parsing or filtering bug, not an AI bug.

## 7. Assumptions I made (tell me if any is wrong)

- Language: **Python**. Tool: any AGENTS.md-aware coding agent.
- LLM use is **optional and small**; the engine must also run with `--no-llm` using a rule-based fallback.
- I could not open the GitHub repo page (access error) but its contents match your uploaded README/AGENTS.md; the Gemini share link only returned a sign-in shell, so I used your PDF export of that chat instead. Its plan was sound at a high level but contained one important mistake (see `01`).
- Token pricing is not invented here; fill real numbers from your provider's pricing page into `usage_report.md`.
