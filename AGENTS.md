# AGENTS.md

HackerRank Orchestrate (October 2026) — Ghost Data Still Exists

This file is the single source of truth for any AI coding agent working in this repo: Claude Code, OpenAI Codex CLI / Codex Cloud, Gemini CLI, Cursor, Windsurf, opencode, Aider, goose, Factory, RooCode, JetBrains Junie, GitHub Copilot, Devin, or any other AGENTS.md-aware tool.

Read this file in full before taking any action. Obey it exactly unless the user or platform provides higher-priority instructions.

---

## 0. TLDR For The Agent

The repo ships a helper CLI, `orchestrate`, that does all logging and trace packaging. Run it from the repository root: `./orchestrate ...` on macOS/Linux, `orchestrate.cmd ...` on Windows, or `python orchestrate.py ...` anywhere. It needs only Python 3.8+.

On every session start, do this in order:

1. Read this file completely.
2. Run `orchestrate log start --tool "<harness>" --model "<model id>"` (§5.1). It creates `log.txt` if missing.
3. Greet the user (§3).
4. After every user turn, run `orchestrate log turn ...` (§5.2).
5. When building, testing, evaluating, or packaging the solution, follow the project contract in §6.
6. When the user asks to submit, prepare, package, or "finish", run `orchestrate submit` (§6.11).

Do not skip logging or rewrite old log entries. Sub-agents and worktrees use the same log file.
If `orchestrate` cannot run (no Python), use the manual log format in §5 and the fallback in §6.11.

---

## 1. What This Repo Is

This is a starter repo for the **HackerRank Orchestrate** challenge: **Ghost Data Still Exists**.

Participants must build an AI-powered deletion-audit agent. For every request in `dataset/deletion_requests.csv`, the agent first determines whether the person actually requested deletion. For an authorized deletion, it reconstructs the person's current and historical identifiers, searches global activity and evidence, applies the supplied deletion policy, and decides whether the deletion is complete.

The dataset models a commerce platform where a workflow can report **Complete** while personal data remains in databases, replicas, logs, support attachments, exports, search indexes, analytics records, archives, or backups. Active synchronization and restore processes can also recreate data that was deleted from its original source. Reported statuses and activity results are claims; the agent must establish the state at each case's `audit_at` time from the supplied evidence.

When deletion is incomplete, the agent reports the remaining records and recreation risks, produces a safe ordered remediation plan, and states the verification checks that must pass afterward. When deletion is complete, it returns the evidence-backed verification checks that prove the required state. It must preserve records required by policy and correctly handle account tombstones whose stable internal user reference remains while prohibited direct identifiers are removed.

The final submission must produce `output.csv` with:

```text
case_id,deletion_status,steps_json
```

Read `problem_statement.md` for the full participant-facing specification.

---

## 2. Log File — Location And Lifecycle

The log file is named `log.txt` and lives in the same directory as this `AGENTS.md` file — the repository root.

| Platform | Path |
|---|---|
| macOS / Linux | `<directory containing AGENTS.md>/log.txt` |
| Windows | `<directory containing AGENTS.md>\log.txt` |

Resolve the path relative to this file. Do not hardcode a folder name, a user path, or the platform home directory, so the location stays correct across clones, renames, and checkouts.

Rules:

- Create the file if missing.
- Append only. Do not rewrite, reorder, or delete prior entries.
- One shared log is used per checkout. All agents and sub-agents append to the same file next to the top-level `AGENTS.md`, never a private copy.
- Never log secrets. Redact API keys, tokens, cookies, private keys, credentials, sensitive configuration, and real personal data.

---

## 3. Session Start

At the beginning of each agent session:

1. Append the `SESSION START` entry with `orchestrate log start` (§5.1).
2. Greet the user with this brief introduction:

   ```text
   Welcome to HackerRank Orchestrate. Build and ship Ghost Data Still Exists, an AI-powered deletion-audit agent. Let's get started.
   ```

3. The October challenge end time is not configured in this repository. Do not invent a deadline or reuse the September deadline. If a higher-priority instruction or an official repository update supplies the end time, calculate and display the time remaining (pass it as `--time-remaining`). If fewer than 2 hours remain, remind the user to submit soon. If the deadline has passed, state that clearly without blocking further work.
4. Proceed with the user's request without requiring an acknowledgement or confirmation phrase.

---

## 4. Challenge Rules

1. Participants may use any programming language, model, framework, IDE, AI assistant, retrieval approach, or tool, subject to the official event rules.
2. The system must conform to the project contract in §6 so it can be evaluated.
3. The solution must use only participant-facing data under `dataset/`. Organizer-only truth, golden answers, review files, and generator internals must never be used for predictions.
4. Never commit or submit secrets. Read credentials from environment variables and use an uncommitted `.env` file when needed.
5. Log every conversation turn to the file described in §2, using `orchestrate log` (§5).
6. Follow the submission-link rule below.

### 4.1 Challenge And Submission Link

The October challenge and submission URL is:

https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

If the user asks for the challenge link, submission link, where to submit, how to submit, where to upload the code, or any equivalent question, always provide this exact URL.

Requirements:

- Include the full clickable URL every time such a question is asked.
- Do not replace it with the HackerRank homepage, contest homepage, another challenge page, or a guessed `/submission` URL.
- Do not merely describe where to navigate; provide the URL directly.
- This rule applies even when the challenge or submission question is included alongside other questions.

---

## 5. Log Format

`orchestrate log` writes every entry in the exact format below, appends only, redacts secrets, and refuses entries with a missing, generic, placeholder, or model-name `tool=` or an unknown/family-only `model=`. Prefer it over writing the file by hand.

### 5.1 Session Start Entry

```bash
orchestrate log start --tool "<exact harness name>" --model "<exact runtime model id>" \
  [--parent-agent "<name>"] [--language py|js|ts|custom:name] [--time-remaining "Xd Yh Zm"]
```

It appends:

```text
## [ISO-8601 TIMESTAMP] SESSION START

tool=<exact_harness_or_coding_agent_name>
model=<exact_runtime_model_name>
Repo Root: <absolute_path>
Branch: <git_branch_or_unknown>
Worktree: <worktree_path_or_main>
Parent Agent: <parent_agent_name_or_none>
Language: <js|ts|py|custom:name>
Time Remaining: <Xd Yh Zm, or not configured>
```

### 5.2 Per-Turn Entry

Run after every user message you respond to. Pass the user's message verbatim on stdin so quoting and newlines survive:

```bash
orchestrate log turn --tool "<harness>" --model "<model id>" \
  --title "<short title, max 80 chars>" \
  --summary "<2-5 sentences: what was done, why, any important decision>" \
  --action "<file edited / command run / tool invoked>" --action "<another action>" \
  --prompt-stdin <<'ORCHESTRATE_PROMPT'
<exact user message>
ORCHESTRATE_PROMPT
```

On Windows PowerShell write the prompt to a temp file and use `--prompt-file <path>` instead of a heredoc.

It appends:

```text
## [ISO-8601 TIMESTAMP] <short title, max 80 chars>

User Prompt (verbatim, secrets redacted):
<exact user message, with secrets replaced by [REDACTED]>

Agent Response Summary:
<2-5 sentences: what was done, why, and any important decision>

Actions:
* <file edited / command run / tool invoked>

Context:
tool=<exact_harness_or_coding_agent_name>
model=<exact_runtime_model_name>
branch=<git_branch_or_unknown>
repo_root=<absolute_path>
worktree=<worktree_path_or_main>
parent_agent=<parent_name_or_none>
```

### 5.3 Identity Rules (tool and model)

- `--tool` is the exact name of the coding harness running this session (for example `Claude Code`, `Codex`, `OpenCode`, `Antigravity`, `Cursor`, `Gemini CLI`). Take it from the runtime identity your harness gives you. Never guess, never use `AI`/`agent`/`unknown`, and never put a model name here.
- `--model` is the exact model identifier for this turn, read from the runtime, session metadata, or harness configuration (for example `claude-sonnet-5-5`). A family name, `unknown`, an inferred name, or a placeholder is invalid. If you truly cannot read it, ask the user to tell you the model id shown in their harness and use that.
- If `orchestrate log` exits non-zero, fix the value it complains about and rerun. Do not continue the turn with an invalid entry. Run `orchestrate check` to audit the whole file at any time.

### 5.4 Sub-Agent And Worktree Rules

- Sub-agents must log their own entries using the same file, with `--parent-agent` set to the parent agent's name.
- Worktrees use the same shared log file next to the top-level `AGENTS.md`, not a per-worktree copy (run the CLI from the top-level checkout, or pass `--repo <top-level path>`).

### 5.5 What Not To Log

- API keys, tokens, session cookies, OAuth codes, credentials, or private keys.
- Sensitive configuration or real personal data.
- Full contents of large files or binary blobs. Reference them by path instead.

---

## 6. Project Contract

### 6.1 Dataset Contract

Participant-facing files are inside `dataset/`.

```text
dataset/
├── deletion_requests.csv
├── sample_deletion_requests.csv
├── sample_output.csv
├── user_identities.csv
├── user_audit_log.csv
├── system_activity.csv
├── deletion_rules.csv
├── evidence_files.csv
├── output.csv
└── evidence/
    ├── databases/
    ├── documents/
    ├── images/
    ├── logs/
    ├── records/
```

- `deletion_requests.csv` contains 518 evaluation requests. Produce exactly one output row for every `case_id` in this file.
- `sample_deletion_requests.csv` contains 32 public requests. `sample_output.csv` contains their correct outputs and demonstrates the required decision and serialization format.
- `user_identities.csv` contains the current identity snapshot for each user, including the stable `user_id`, name, email, phone, email hash, and snapshot update time.
- `user_audit_log.csv` records historical changes to identity fields. Use it with the current snapshot to recover identifiers that may still appear in older systems and evidence.
- `system_activity.csv` is a global stream of deletion, synchronization, export, backup, restore, indexing, and audit events. Its rows may describe unrelated people. Determine resource state from the available evidence rather than trusting workflow or operation results alone.
- `deletion_rules.csv` defines the required action for each data category and condition. Actions include deleting the whole record, redacting prohibited identifiers, anonymizing the record, retaining it, or preserving an account tombstone with only the permitted stable reference.
- `evidence_files.csv` is the manifest for evidence under `dataset/evidence/`. It maps each `file_id` to its path, source origin, and capture time. The manifest does not identify which case or user a file concerns; the solution must connect evidence through its contents and identifiers.
- `output.csv` is the blank prediction template. The final completed `output.csv` must be written at the repository root for submission.
- Evidence may be provided as PDF documents, application screenshots, logs, JSON, plain-text records, and SQLite-compatible SQL snapshot exports. SQL files are readable text and may be executed with SQLite.

Only `deletion_requests.csv` requires predictions. Other participant-facing files provide identity, policy, activity, and evidence context. Global data can contain decoys and unrelated records.

Organizer-only files live outside `dataset/` and must never be used for predictions, prompt examples, hardcoded labels, or evaluation-time shortcuts.

### 6.2 Input And Time Contract

Each request has these fields:

```text
case_id,email,requested_at,reported_status,reported_at,audit_at,request_text
```

- `case_id` uniquely identifies the request and its output row.
- `email` is the identity supplied with the request. It may be a current or historical email address.
- `requested_at` is when the request was submitted.
- `reported_status` is the deletion workflow's claim: `COMPLETE`, `PARTIALLY_COMPLETE`, or `NOT_STARTED`.
- `reported_at` is when that claim was reported.
- `audit_at` is the cutoff for the required answer.
- `request_text` contains the person's request and may be written in different languages. Determine whether it actually authorizes deletion.

Use only information available at or before `audit_at` when deciding the case. Evidence created later must not change the answer for that case.

### 6.3 Required Output

The solution must write `output.csv` with these exact columns, in this order:

```text
case_id,deletion_status,steps_json
```

Requirements:

- Produce exactly 518 data rows: one for every `case_id` in `dataset/deletion_requests.csv`.
- Sort rows by `case_id`.
- Set `deletion_status` to `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
- Use `NOT_APPLICABLE` with `steps_json=[]` when the request does not authorize deletion.
- Encode `steps_json` as a valid JSON array. The grader ignores JSON object-key order and whitespace but preserves array order.
- Number steps consecutively from `1`.
- Order phases as `FINDING`, then `REMEDIATION`, then `VERIFICATION`.

Each step contains exactly these fields:

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

For a `COMPLETE` case, include only evidence-backed verification steps proving the state at `audit_at`. For an `INCOMPLETE` case, include the findings, the complete ordered remediation plan, and the checks that must pass after remediation. Findings cite participant-visible evidence. Proposed remediation and future verification steps use an empty `evidence_id`.

### 6.4 Allowed Step Operations

Findings:

| Operation | State | Meaning |
|---|---|---|
| `REPORT_REMAINING_RECORD` | `PRESENT` | A record that should have been deleted still exists. |
| `REPORT_EXPOSED_PII` | `PRESENT` | A record may remain, but identifiers that policy requires to be redacted or anonymized are still exposed. |
| `REPORT_ACTIVE_DATA_FLOW` | `ACTIVE` | An active process can copy or recreate the user's data. |
| `REPORT_RESTORE_RISK` | `ACTIVE` | A backup or restore path can bring deleted data back. |

Remediation:

| Operation | State | Meaning |
|---|---|---|
| `DISABLE_DATA_FLOW` | `DISABLED` | Stop a process that can copy or recreate the data. |
| `BLOCK_RESTORE` | `BLOCKED` | Prevent the affected backup from restoring the user's data. |
| `DELETE_RECORD` | `ABSENT` | Remove the entire record. |
| `REDACT_RECORD` | `REDACTED` | Keep the record but remove the identifying fields required by policy. |
| `ANONYMIZE_RECORD` | `ANONYMIZED` | Keep the record after irreversibly unlinking it from the user. |

Verification:

| Operation | State | Meaning |
|---|---|---|
| `VERIFY_RECORD_ABSENT` | `ABSENT` | Confirm that a record no longer exists. |
| `VERIFY_RECORD_PRESENT` | `PRESENT` | Confirm that a policy-required retained record still exists. |
| `VERIFY_RECORD_REDACTED` | `REDACTED` | Confirm that required identifying fields were removed. |
| `VERIFY_RECORD_ANONYMIZED` | `ANONYMIZED` | Confirm that the record can no longer be linked to the user. |
| `VERIFY_DATA_FLOW_DISABLED` | `DISABLED` | Confirm that the relevant data flow is inactive. |
| `VERIFY_RESTORE_BLOCKED` | `BLOCKED` | Confirm that the affected data cannot be restored. |

Do not invent additional phases, operations, or states.

### 6.5 Deletion Decision Rules

- First determine whether `request_text` authorizes deletion. A request for access, correction, export, marketing opt-out, or another non-deletion action is `NOT_APPLICABLE`, even if other fields resemble a deletion case.
- Resolve both current and historical identifiers for the subject. The request email may match either form.
- Reconstruct the true state at `audit_at`. Ignore later evidence and do not accept `reported_status` or `reported_result` as proof.
- Apply `deletion_rules.csv` to every relevant record. Do not delete data that policy requires to be retained, redacted, anonymized, or preserved as a tombstone.
- For an `ACCOUNT_TOMBSTONE`, preserve the stable subject reference and remove the name, email, phone, email hash, and any other direct identifiers required by the applicable `REDACT` rule.
- A deletion is `COMPLETE` only when every relevant copy has the required treatment, every required retained record remains available, and no active sync, import, or restore path can recreate prohibited data.
- For an incomplete case, report every relevant policy violation and recreation risk supported by participant-visible evidence.
- Within remediation, disable data flows and block unsafe restores before changing dependent records. Process downstream copies before their source records when the dependency requires it.
- Verification must cover the required final state for each remediated record or process.

### 6.6 Evidence Rules

- Treat activity logs, workflow statuses, and system messages as claims unless the available evidence establishes the resulting state.
- Use `evidence_files.csv` to locate files, then inspect their contents. Do not infer case membership from the manifest alone.
- Match evidence through current identifiers, historical identifiers, hashes, resource IDs, system IDs, timestamps, and other grounded links.
- Images and PDFs are ordinary business artifacts such as invoices, support records, handover documents, and internal product screens. Extract the facts they contain; do not expect an explicit deletion verdict.
- SQL evidence can contain primary, regional, reporting, or failover replicas. Compare the relevant tables and snapshot time when investigating replication drift.
- A finding must use the participant-visible `file_id`, `activity_id`, or `audit_id` that proves it.
- A verification step for a `COMPLETE` case must cite the evidence that proves the current compliant state.
- Remediation steps and post-remediation verification steps for an `INCOMPLETE` case describe future work and therefore use `evidence_id` as an empty string.
- Never cite organizer-only truth or an evidence item captured after the case's `audit_at`.

### 6.7 Constraints That Make The Submission Evaluable

- Be runnable from the terminal.
- Read the provided files from `dataset/`.
- Write the completed `output.csv` at the repository root.
- Do not use organizer-only files, hardcoded golden labels, or case-family shortcuts.
- Keep behavior deterministic where possible, including ordering and JSON serialization.
- Read secrets from environment variables only.
- Include clear setup and run instructions in the submitted `README.md`.
- Ensure a clean run can process all 518 cases and produce exactly one valid row per case.

### 6.8 Evaluation And Token Usage

The submitted `code.zip` must include:

```text
evaluation/evaluation_report.md
evaluation/usage_report.md
```

`evaluation/evaluation_report.md` must contain:

- case-level deletion-status accuracy;
- step-level and field-level accuracy;
- sequence accuracy;
- at least three additional evaluation cases created by the participant; and
- failures found and improvements made.

`evaluation/usage_report.md` must summarize the final full-dataset run that produced `output.csv`, including:

- model providers and model names;
- model-call counts;
- input and output tokens;
- total and average tokens per request;
- estimated total and per-request cost; and
- per-model and overall totals when multiple models are used.

Write the required evaluation metrics, custom cases, and usage details directly in these Markdown files. Never include API keys, credentials, or sensitive configuration values.

### 6.9 Submission Artifacts

The participant submission contains:

| Item | Description |
|---|---|
| `code.zip` | Runnable solution, prompts, configuration, `README.md`, and the `evaluation/` reports |
| `output.csv` | One answer row for every evaluation request |
| `chat_transcript` | The root `log.txt` file generated by the coding agent |
| `agent-trace.zip` | Raw agent session traces for this challenge, built by `orchestrate submit` (§6.11) |
| AI interview | Explanation of the architecture, investigation approach, remediation planning, and evaluation |

Do not include `dataset/`, virtual environments, dependency caches, nested archives, API keys, credentials, real personal data, or sensitive configuration in `code.zip`.

### 6.10 Reasonable Entry Points

There is no required language. If using Python, `code/main.py` is a good entry point. If using another language, document the exact setup and run command clearly in the submitted README.

### 6.11 Agent Trace And Submission Helper

Organizers ask for the complete agent trace (prompts, responses, tool calls) of every session used on this challenge, as `agent-trace.zip`. Do not collect it by hand. Run, from the repository root:

```bash
orchestrate submit          # validates output.csv + log.txt, builds agent-trace.zip, prints the submit checklist
```

Launchers: `./orchestrate` (macOS/Linux), `orchestrate.cmd` (Windows), or `python orchestrate.py` / `python3 orchestrate.py` anywhere. Other commands: `orchestrate trace` (traces only), `orchestrate check` (validation only), `orchestrate doctor` (what was checked and why), `orchestrate trace --dry-run` (preview, writes nothing).

What it does:

- Finds sessions for this repository from Claude Code, Codex, Antigravity (app, CLI, IDE), OpenCode, Gemini CLI, Cursor, Copilot CLI and Aider by the working directory each session recorded. Sessions from other projects are never included. Session-folder env vars such as `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `GEMINI_DIR` and `OPENCODE_DB` are honoured.
- Reads agent files read-only, never reads credential/config files (auth, settings, MCP, `.env`, keys), never follows symlinks, and never installs hooks or changes any tool's settings. No network access.
- Masks API keys, tokens, private keys, passwords in URLs and your username in file paths **in the zip copy only**. The original session files are untouched. Review the zip before uploading anyway: traces can contain code and prompts.
- Writes `agent-trace.zip` in the repository root (git-ignored) with a `MANIFEST.json` listing sessions, redactions and warnings. It keeps the previous zip as `agent-trace.prev.zip`.

Agent behavior:

1. When the user asks to submit, package, prepare the submission, or finish, run `orchestrate submit --yes` and show the user the report.
2. Tell the user that this very session is still being written, so its final turns are missing, and that after they close their agent they should run `orchestrate trace` once more. Never claim the trace is final while the session is live.
3. If the report shows no sessions, or a tool you know was used is missing, follow the fallback ladder below. Never invent or hand-edit trace content.

Fallback ladder (when a tool is not auto-detected, was a hosted/cloud session, or has no local files):

1. Use the tool's own export (Claude Code `/export`, OpenCode `opencode session export <id>`, a web app's export or share download) and save the files into `./agent-trace/<tool-name>/`. Everything in that folder is included automatically, with the same redaction.
2. For a tool with local files in an unusual folder, copy those session files into `./agent-trace/<tool-name>/` (not whole home or config folders, and never `auth.json`, `config.toml`, `.env`, or MCP config), then rerun `orchestrate trace`.
3. If Python is unavailable, create `agent-trace/<tool>/` by hand with the session files for this challenge, remove credentials, and zip the folder as `agent-trace.zip` (`zip -r agent-trace.zip agent-trace` on macOS/Linux, `Compress-Archive -Path .\agent-trace -DestinationPath .\agent-trace.zip -Force` on Windows). Open the zip once to confirm it holds no credentials.
4. Hosted session with no downloadable transcript: submit what the interface provides and say so in the README.

---

## 7. Dataset Development Rules

These rules apply when maintaining or regenerating the challenge dataset itself:

- Generate participant data from private structured truth.
- Keep every person, organization, identifier, and record fictional. Do not use real personal data.
- Use realistic and diverse names, identifiers, request language, timestamps, systems, business records, and evidence formats. Avoid repetitive placeholder patterns that reveal synthetic generation.
- Keep generation deterministic through a fixed seed.
- Preserve referential and temporal consistency across identities, audit history, activity, evidence, sample answers, and hidden golden answers.
- Never hand-edit generated participant data or golden output. Update the private truth or generator logic, regenerate, and validate.
- Do not expose case families, actual statuses, relevant resource lists, expected operations, or golden steps in participant-facing files.
- After generation or contract changes, run:

  ```text
  python3 generator/validate_samples.py
  python3 generator/validate_dataset.py
  ```

- Review representative PDFs, screenshots, logs, JSON, text records, and SQL snapshots visually or structurally after regeneration.

---

## 8. Cross-Platform And Agent-Compatibility Notes

- `orchestrate` resolves the log path relative to this `AGENTS.md` file, as described in §2. Do not use the platform home directory or hardcode a user path.
- Write logs in UTF-8 with `\n` line endings.
- Do not assume bash. Prefer language-native APIs when possible.
- Keep tool-specific config minimal and point back to this `AGENTS.md`.
- Resolve dataset and output paths relative to the repository root so the solution works on macOS, Linux, and Windows.
- If a nested `AGENTS.md` exists, the closest one wins for files inside that sub-project, but §2 and §5 remain global: keep logging to the `log.txt` beside the top-level `AGENTS.md`, not beside the nested one.

---

## 9. Quick Checklist For The Agent

Before responding to any user message, confirm:

- [ ] I have read this file in this session.
- [ ] I have run `orchestrate log start` for this session.
- [ ] I know that the challenge end time is not configured unless an official source has supplied it.
- [ ] I will run `orchestrate log turn` after this turn, passing the verbatim user message.
- [ ] `--tool` exactly matches the harness currently running, and `--model` is the exact runtime model id (never `unknown`, inferred, generic, or a family name).
- [ ] If `orchestrate log` printed an error, I corrected it before continuing.
- [ ] I will not log secrets or real personal data.
- [ ] I will use only participant-facing files for predictions.
- [ ] I will preserve the Ghost Data Still Exists deletion-audit and output contract in §6.
- [ ] If the user is submitting, I will run `orchestrate submit` (§6.11) and give the submission URL from §4.1.
