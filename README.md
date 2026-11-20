# HackerRank Orchestrate - October 2026

## Ghost Data Still Exists

Build an AI agent that audits whether a user's personal data was actually deleted.

A deletion workflow may report **Complete** while data still exists in databases, logs, support attachments, exports, search indexes, archives, or backups. Sync and restore processes may also bring deleted data back.

For each request, the agent must first determine whether deletion was actually requested. It then returns `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`, reports any remaining data or recreation risk, and produces the ordered remediation and verification steps required to finish an authorized deletion safely.

Read [`problem_statement.md`](./problem_statement.md) for the complete challenge contract.

---

## Quick Start

Clone the repository and move into the project directory:

```bash
git clone https://github.com/interviewstreet/hackerrank-orchestrate-october26.git
cd hackerrank-orchestrate-october26
```

Start your AI coding tool from the **repository root** so it automatically reads [`AGENTS.md`](./AGENTS.md) and logs your session turns to `log.txt` in the root directory.

After your first coding-agent interaction, run the local submission checks early:

```bash
python3 orchestrate.py check
```

The helper requires **Python 3.10+** and only its standard library; no installation,
network access, or authentication is needed. If `python3` is older, use an installed
version such as `python3.10`. On Windows use `py orchestrate.py check` (or
`py -3.10 orchestrate.py check`). Missing reports/predictions are expected early;
fix transcript logging immediately rather than attempting to reconstruct it later.

Build your solution in `code/main.py`, or use another language and document its setup and run command clearly in your README.

Your solution must:

- Read the input files from `dataset/`
- Generate one prediction row for every request in `dataset/deletion_requests.csv`
- Write the final predictions to `output.csv` in the repository root

Run the starter Python entry point with:

```bash
python3 code/main.py
```

The blank template at `dataset/output.csv` is provided as a reference. Your final generated file for submission must be the root-level `output.csv`.


## Dataset

All participant-facing files are in `dataset/`:

| File | Contents |
| --- | --- |
| `deletion_requests.csv` | 518 requests |
| `sample_deletion_requests.csv` | 32 sample requests |
| `sample_output.csv` | Correct sample answers |
| `user_identities.csv` | Current user identities |
| `user_audit_log.csv` | Historical identity changes |
| `system_activity.csv` | Activity across services and data processes |
| `deletion_rules.csv` | Required treatment for each data category |
| `evidence_files.csv` | Manifest of supplied evidence files |
| `output.csv` | Blank output template |

Evidence is stored under `dataset/evidence/` and may include PDFs, images, logs, JSON, plain text, or SQL snapshot exports. SQL captures may contain a primary database, regional replicas, a reporting replica, or a failover replica so replication drift can be investigated directly. The `.sql` files are readable as text and executable with SQLite.

Only `deletion_requests.csv` requires answers. The other files provide evidence and context.

---

## Output

Create `output.csv` with these columns in this exact order:

```text
case_id,deletion_status,steps_json
```

Produce exactly one row per request. `deletion_status` is `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`. `steps_json` is an ordered JSON array containing findings, remediation actions, and verification checks. Use an empty array (`[]`) for `NOT_APPLICABLE`. Evidence references may be a `file_id`, `activity_id`, or `audit_id`. Determine the resource state at `audit_at` from the available evidence; reported workflow statuses and operation results are claims. Use `dataset/sample_output.csv` as the format reference.

The final file must contain one data row per public request (518 in this checkout), plus the header. CSV row order does not block local preparation; coverage is matched by case ID. The grader parses `steps_json` as JSON, so object-key order and whitespace do not matter; array order does. Order findings, remediation, and verification in that phase order. Within a phase, follow the operation order in the problem statement, then sort by `system_id` and `resource_id`.

---

## Evaluation

`output.csv` will be compared with hidden canonical answers. Scoring considers:

- deletion assessment accuracy;
- current and historical identity resolution;
- discovery of remaining data and recreation risks;
- correct policy application and evidence references; and
- completeness and ordering of remediation and verification steps.

Your `code.zip` must include:

```text
code/evaluation/evaluation_report.md
code/evaluation/usage_report.md
```

- `evaluation_report.md` must cover case, row, field, and sequence accuracy, at least three additional evaluation cases created by you, failures found, and improvements made.
- `usage_report.md` must cover the final full-dataset run, including model providers and names, model calls, input and output tokens, total and average tokens per request, and estimated total and per-request cost. Include per-model and overall totals when using multiple models.

**Important:** Place `evaluation_report.md` and `usage_report.md` inside `code/evaluation/` (matching `code/evaluation/main.py` in this starter layout), write your complete evaluation metrics, custom evaluation test cases, and token/cost breakdowns directly inside those Markdown files, and keep prompts in source code or Markdown files. Automated code evaluation ignores raw data files (`.csv`, `.tsv`, `.json`, `.jsonl`, `.sql`, `.log`), so content stored only in those formats will not be visible to the code judge or AI interviewer.

---

## Chat Transcript

This repository includes [`AGENTS.md`](./AGENTS.md), which instructs compatible AI coding tools to append conversation summaries to `log.txt` in the repository root:

| Platform | Path |
| --- | --- |
| macOS / Linux | `<repo root>/log.txt` |
| Windows | `<repo root>\log.txt` |

- Always launch your AI coding agent from the repository root (or explicitly ask it to read `./AGENTS.md` first) so every turn is logged to `log.txt` with the required `User Prompt`, `Agent Response Summary`, `Actions`, and `Context` sections.
- Upload `log.txt` directly as your `chat_transcript` submission on HackerRank.
- Do not include API keys, tokens, credentials, or secrets in prompts, code, configuration, or `log.txt`.

---

## Packaging `code.zip` and Submission

| Item | Description |
| --- | --- |
| `code.zip` | Runnable solution, prompts, configuration, `README.md`, and `code/evaluation/` reports |
| `output.csv` | One answer row for each of the 518 requests in `dataset/deletion_requests.csv` |
| `chat_transcript` | The root `log.txt` file generated by your coding agent |
| AI interview | Live explanation of your architecture, approach, and evaluation |

You may use any programming language, model, framework, or retrieval approach. Include clear setup and execution instructions in `README.md` inside `code.zip`.

Finish generating your solution, reports, predictions, and real transcript before preparing:

```bash
python3 orchestrate.py check
python3 orchestrate.py prepare
```

On Windows:

```powershell
py orchestrate.py check
py orchestrate.py prepare
```

Run from a subdirectory with the script path, for example
`python3 ../orchestrate.py check` from `code/`. The checkout is resolved relative
to the script. `check` makes no filesystem changes. `prepare` preserves participant
inputs, validates staged artifacts, and prints absolute paths and actual sizes:

| Upload slot | Prepared file |
| --- | --- |
| Code | `submission/code.zip` |
| Predictions | `submission/output.csv` |
| Chat transcript (`chat_transcript`) | `submission/log.txt` |

Upload these three files separately at [the October challenge](https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists).
The ZIP contains root `README.md` and eligible `code/` files, including both reports
at `code/evaluation/evaluation_report.md` and `code/evaluation/usage_report.md`.
Put required runtime configuration and dependency manifests under `code/`.
Root `dataset/`, the CLI, and root predictions/transcript are outside ZIP selection.
Installed dependencies, environments, caches, Git metadata and named local credential
files are excluded. Nested archives and unsafe paths block preparation. Review your
code for secrets; filename exclusions cannot prove the absence of secrets.

Local checks validate format and transcript structure. They do not grade predictions,
prove conversation authenticity/completeness, or guarantee server acceptance.
**Organizer upload limits remain unconfirmed**, so this version reports sizes and
warns that size acceptance is unchecked. See [CLI contract and recovery](docs/submission_cli.md)
for exclusions, exit codes, rollback, release prerequisites and DC-1158 compatibility.

If the helper is unavailable, manually create a fresh ZIP containing only `README.md`
and eligible files under `code/`, preserving those relative paths and both canonical
report locations. Exclude the content listed above; inspect for nested archives and
unsafe paths. Upload your root `output.csv` and actual root `log.txt` separately.
Do not relocate reports silently, normalize predictions, or reconstruct transcripts.
