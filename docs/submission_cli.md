# Submission helper contract and recovery

`orchestrate.py` 1.0.0 implements `orchestrate-october26-v1`, using Python 3.10+
and the standard library. `--version` prints both identifiers. Keep the script at
the checkout root. No package installation, network, login, participant-code
execution, hidden-answer access, scoring, or telemetry is involved.

Run `python3 orchestrate.py check` early, then `python3 orchestrate.py prepare`
when all inputs stop changing. Windows uses `py` instead of `python3`.
Exit codes: 0 completed (warnings possible), 1 validation errors, 2 command/runtime
usage, 3 operational failure (lock, disk/permissions, changed input, verification,
or publication). Diagnostics aggregate independent problems, show at most five
examples per code and include total counts. CSV record numbers are logical records,
not physical lines; blank records are ignored. Standard quoted multiline fields,
BOM and CRLF are accepted. Headers/status/ID strings are exact, without trimming.
JSON rejects duplicate keys and nonstandard constants. There is a 64 MiB CSV-cell
parser bound, not an event upload limit. CSV row order is accepted in any order;
step numbering and phase/table-operation/system/resource ordering are validated.
No evidence correctness, remediation completeness, or policy decision is graded.

Only readable root `README.md` and eligible `code/` files enter a fresh ZIP.
Canonical required reports are `code/evaluation/evaluation_report.md` and
`code/evaluation/usage_report.md`; they must be nonempty UTF-8 Markdown. Evaluation
substance and obvious-looking headings are not used to infer whether work occurred.
The root dataset is never traversed for packaging. Only public
`dataset/deletion_requests.csv` is read to establish expected IDs/count.
Custom fixtures named `dataset` under `code/` remain eligible. Runtime manifests,
lockfiles and custom `lib`, `bin`, `dist` directories remain eligible.

Exact directory-name exclusions (case insensitive): `.git`, `.hg`, `.svn`, `.venv`,
`venv`, `node_modules`, `site-packages`, `__pycache__`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache`, `__MACOSX`. Directories with a `pyvenv.cfg` marker are pruned.
Exact credential names excluded: `credentials.json`, `credentials.ini`, `.netrc`,
`_netrc`, `.npmrc`, `.pypirc`, `id_rsa`, `id_ed25519`, `.aws`, `.ssh`.
Also excluded: `.DS_Store`, AppleDouble `._*`, `*.pyc`, `*.pyo`, `*.pem`, `*.key`,
`.env` and `.env.*`, except `.env.example` and `.env.sample`. These exclusions affect
only the ZIP; no source file is deleted. They cannot detect every secret or renamed
copy of the supplied dataset. Root generated bundles are outside selection; archives
inside `code/` block preparation, including `code.zip`. Archive suffix checks cover
ZIP/tar/gzip/tgz/7z/RAR (case insensitive); bounded signatures cover ZIP/gzip/7z/RAR
and tar's ustar marker. This is not exhaustive format detection.

Selected symlinks, junctions/reparse points, nonregular files, escaping paths,
Windows-unsafe names and normalized/case-colliding member names are rejected.
ZIP entries preserve POSIX relative paths and executable mode where available.
Entry order is stable; metadata means ZIP bytes need not be reproducible.

Transcript recognition accepts dated AGENTS entries, treating SESSION START
separately, and requires nonempty ordered User Prompt, Agent Response Summary,
Actions and Context bodies in at least one turn. Fenced/indented code and blockquoted
examples are ignored. Empty/binary/undecodable and session-only transcripts block.
Incomplete later turns, decorated headings and missing/obvious placeholder metadata
warn. Structural recognition does not prove authenticity or complete capture. The
helper never generates missing reports or edits predictions/transcripts.

## Publication and recovery

`check` writes nothing, including bookkeeping. `prepare` holds an exclusive
`.orchestrate.lock`, snapshots selected file identity/size/timestamps, stages beside
`submission/`, builds and verifies ZIP members/CRC, rechecks staged CSV/transcript,
and checks input identity again before publication. Finish all file generation
first: these checks detect ordinary edits, not an atomic tree snapshot or an
adversarial filesystem race. Files created after selection may require another run.

Only three deliverables enter `submission/`. `.orchestrate-state.json` outside it
records ownership and artifact SHA-256 hashes. An unknown, symlinked, modified, or
extra-file destination is refused; move it aside yourself to preserve its contents.
The ownership marker is bookkeeping, not a security boundary against local editing.

On rerun, a publishing journal is written before moving the old known bundle to a
unique `.orchestrate-backup-*`, then renaming the completed `.orchestrate-stage-*`
to `submission/`. Normal publication failures restore the previous directory and
marker. On success the marker becomes ready and only the known backup is removed.
This is not a crash-atomic three-file replacement on every platform.

After interruption, the next preparation refuses to guess which files to delete:

1. Confirm no preparation is running. Inspect the exact `.orchestrate.lock` path
   reported; remove that stale lock manually only after confirming this.
2. Preserve/inspect `submission/`, the exact stage/backup paths reported, and
   `.orchestrate-state.json`. Never delete an unknown backup blindly. A publishing
   journal lists `stage`, `backup`, new `hashes`, and the `previous` ready marker.
3. To restore the previous bundle when `submission/` is missing, rename the listed
   backup to `submission/`. Confirm it contains exactly three regular artifacts and
   their SHA-256 hashes match `previous.hashes`. Restore the marker to the journal's
   `previous` object. Move the unused stage outside the checkout for inspection.
4. If the new directory is already present, first move it aside for inspection
   before restoring the old bundle. If there was no previous bundle, move all
   generated candidates aside and move/remove the journal to restart fresh.
5. For ambiguous states or a ready marker with a leftover backup, preserve all
   candidates outside the checkout and remove the bookkeeping marker to start a
   new first publication. This does not alter source inputs. Keep preserved copies
   until the newly prepared artifacts are inspected. Rerun `prepare` afterward.

A stale stage created before journaling is also refused. Inspect/move it aside
manually; it is never silently reused. A failed run never claims an older bundle
was newly prepared. Run again after correcting permissions, disk space, or input
changes. The original CSV/transcript/reports/source are never rollback targets.

## Release prerequisites and DC-1158 coordination

**Upload limits are unresolved.** The authoritative server code compares payload
bytes against each event `DataSetFile.upload_limit`, not a universal constant.
No October per-slot organizer values were found in the inspected repository.
An attempt to read the official challenge API was inaccessible, and the Linear
connection requires reauthentication. Before release, an organizer must supply the
actual Code/Predictions/Chat transcript records' byte limits, encode them in
`UPLOAD_LIMITS`, and verify the upload-page labels. Until then the helper prints a
warning, reports actual prepared sizes, and does not guarantee size acceptance.
Injected-limit tests exercise size rejection without inventing production values.

The inspected community `OrchestrateSubmissionValidator` checks CSV header/count
against server-side shape and scans transcript headings; warnings allow upload.
It has no ZIP content branch. DC-1158 server work is separate: do not execute this
participant-editable helper on the server or automatically change warning policy.
Intentional stricter CLI checks include ID uniqueness/coverage, statuses, JSON
fields/types/order, nonempty transcript section bodies, required reports and ZIP
selection/unsafe paths. The helper derives IDs from public requests only.
`VERIFY_DATA_FLOW_DISABLED` maps to `DISABLED`.

`tests/submission_cli/contract_cases.json` provides portable synthetic CSV/log
strings and expected CLI errors for Ruby parity work. Ruby CSV currently strips
whitespace and skips blanks; Python skips blank records but rejects header/value
whitespace. Both need explicit shared-fixture decisions for malformed quotes,
BOM/CRLF/multiline fields, extra cells and duplicate headers. Server error wording
may differ. Ruby execution/parity and deployed behavior have not been verified.
Ticket details for DC-1164/DC-1158 could not be fetched due to Linear authentication.
Reconcile those details, upload-page wording, confirmed size limits and shared
fixture outcomes with organizers before release.

CI config covers macOS, Linux, Windows on Python 3.10 and 3.13, including directory
publication, lock contention, rollback and interruption tests. Windows symlink tests
skip if OS privilege is unavailable; the Windows junction test exercises reparse
handling separately. Configuring CI is not evidence it ran. Local results and the
release report must distinguish actual executions from this matrix. Full private
October corpus replay is not part of the synthetic suite; no private submissions,
transcripts, identity mappings, or download links are included.


## Local verification on 20 November 2026

On macOS, the 35-test suite completed on Python 3.10.19 and 3.13.12: 34 tests
passed and the Windows-only junction test skipped in each run. The suite includes
synthetic end-to-end preparation from a different working directory, repeated runs,
byte preservation, two-process lock contention, staged corruption, publication and
marker failures, failed rollback, and explicit interruption/recovery.
`git diff --check` passed. The real starter `check` reports missing predictions and
two participant reports, as expected; none were fabricated. The system Python 3.9
produces the documented runtime requirement error. Linux/Windows CI execution,
Ruby shared-fixture parity and private-corpus review have not been run locally.
