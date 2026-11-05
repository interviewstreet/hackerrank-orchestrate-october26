# EraSight frontend — Member One

React, TypeScript, Vite, Tailwind CSS, Three.js, React Three Fiber, Drei, Motion, Recharts and lightweight custom components. Requires Node 22 or later.

From the repository root:

```powershell
cd code/frontend
npm.cmd install
npm.cmd run dev
```

Open http://127.0.0.1:5173. `npm.cmd` avoids the Windows PowerShell script execution-policy restriction; on macOS/Linux use `npm`.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

Live backend results are the default. Set `VITE_DATA_MODE=demo` explicitly for the clearly labeled demonstration workspace with six fictional cases, including complete and incomplete outcomes. Navigation, search, result filters, case selection, 3D globe rotation/zoom, node inspection, finding-path highlighting, recommended actions, evidence capture history, analytics, and per-case JSON download work locally. The canvas has a keyboard-accessible node list. No graph relationship is inferred from live data.

To use Member Two's results, copy `.env.example` to `.env.local`, set `VITE_DATA_MODE=live`, set the API base URL and restart Vite. See [CONTRACT.md](./CONTRACT.md). Live API failures remain visible with Retry. The local presentation API and Slack route are available through code/server.py. Slack delivery requires live engine data; demo sends are disabled. Email actions use the existing secure adapter; see Phase 4 below.

Never set webhook URLs or provider keys in a `VITE_` variable: those values are public browser configuration. This frontend does not alter the dataset, engine, or challenge `output.csv`.

## Creative redesign

The overview uses a rounded white studio frame, smaller sentence-case system typography and circular #007BFF light exposure. The globe renders every supplied node with an instanced mesh; edges use the supplied relationships only. A fixed spherical rim and depth layers preserve the silhouette. A separate non-interactive light scaffold adds visual density; it is not counted as evidence and disappears during path inspection. Find a node explains this distinction. Six fictional fixture cases remain clearly labeled. No new analytical results were created for this redesign.

Click a node or choose it from **Find a node** to inspect its findings, evidence references and ordered recommended actions. Controls support rotation, zoom, reset, alert filtering and animation pause. Search and system/type filters are available in the node browser. Reduced-motion preferences disable idle rotation, pulse, exposure animation and moving transitions. Offscreen and hidden-tab globes stop their continuous render loop.

Three.js is loaded as a separate chunk. The renderer uses adaptive pixel ratio and a static SVG projection plus the same keyboard-accessible node browser if WebGL2 is unavailable or the context is lost. The existing case-result API contract remains unchanged.

The current implementation was compared with the inline IMAGE B at its 1800 x 873 viewport. See DESIGN.md for measured corrections and screenshot locations. Resting desktop graph controls appear on hover or keyboard focus; mobile controls stay visible.


## Run Slack Phase 1

1. Install Python 3.10+, Node 22+, Poppler (`pdftotext`) and Tesseract (`tesseract`); both parser commands must be on PATH. The API refuses startup if any evidence file fails processing.
2. Keep `SLACK_WEBHOOK_URL`, `SLACK_BOT_TOKEN` and `SLACK_REPORT_CHANNEL_ID` in the ignored root `.env` (see HTML report delivery below). Never copy it into frontend variables or browser requests. Real process environment variables take precedence over `.env`.
3. From the repository root run `python code/server.py`. It loads all cases from Member Two's engine at startup; restart after changing the dataset or server environment.
4. Set `VITE_DATA_MODE=live` and `VITE_API_BASE_URL=` in `code/frontend/.env.local`, then run `npm.cmd run dev` from this frontend directory. Use http://127.0.0.1:5173 (or the production preview at port 4173). Restart Vite after changing frontend environment variables.
5. Open an investigation and click **Send Slack report**. During delivery the button is disabled. A confirmed response shows the sent case ID; failures appear in the existing communication area. The webhook's configured channel receives the message, normally #erasight-alerts. Check that the case/status, controlled findings, systems and remediation are correct and that no personal identifiers appear.

Manual negative checks: temporarily remove SLACK_WEBHOOK_URL and restart the API to verify missing-configuration feedback; use a test webhook for rejected-delivery checks. Never point test failures at a production channel. Requests without the session/CSRF/origin checks are rejected. Repeated confirmed sends are blocked briefly. Demo cases do not post.

Checks: `python -m pytest code/tests/test_slack.py` from the root, and `npm.cmd test` / `npm.cmd run build` here. Tests mock Slack entirely. No live Slack delivery is required for automated checks. Full backend tests remain `python -m pytest code/tests`.


### HTML report delivery

Keep the existing root `SLACK_WEBHOOK_URL`. Add root `.env` values `SLACK_BOT_TOKEN` (bot scopes `files:write` and `files:read`) and `SLACK_REPORT_CHANNEL_ID` (the webhook's channel). Invite the bot to the channel and reinstall the Slack app after adding scopes. Restart `python code/server.py`. Keep these settings server-side; never add a bot token to a `VITE_` variable.

The existing **Send Slack report** button sends the overview through the Incoming Webhook after uploading a sanitized HTML report to Slack. The link opens a Slack-authenticated file page where authorized channel members can download the HTML. The file contains all supplied findings, safe evidence references, affected systems, ordered remediation recommendations and verification checks, without raw evidence or personal identifiers.

Live check after configuration: open a real case in live mode, send once, verify the header, overview and download link order, then open the link as a channel member and download the HTML. Confirm that an account without channel access cannot retrieve it. A missing configuration or failed upload must show the existing error state without a success claim. Mocked coverage: `python -m pytest code/tests/test_slack.py`.


If upload sharing returns `not_in_channel`, open the destination channel's Details, copy its channel ID into root `SLACK_REPORT_CHANNEL_ID`, and add the **EraSight** app that owns the configured bot token through Details > Integrations > Add apps. A successful webhook post does not prove the upload bot is a channel member. The integration does not require `channels:join`; invite it manually when self-join is unavailable. Save server credentials in the root `.env`, not `code/frontend/.env.local`, and restart the API after changing them.


## Phase 2: backend API connectivity

Run `python code/server.py` from the repository root with the existing Python dependencies and PDF/OCR tools installed. The server computes Member Two's latest merged engine results once at startup. Keep `VITE_DATA_MODE=live` and `VITE_API_BASE_URL=` in `code/frontend/.env.local`; Vite forwards `/api` to `http://127.0.0.1:8000`. Start Vite with `npm.cmd run dev --prefix code/frontend`. Restart the API after backend or dataset changes, and restart Vite after frontend environment changes.

All four pages share the existing `GET /api/cases` response:

- Overview: engine status totals, applicable-request completion rate, selected-case findings and the 3D graph.
- Investigations: real case rows, status filtering, audit/request timestamps, workflow claims, ordered actions and verification.
- Evidence: the selected case's actual resource nodes, supplied edges, evidence references and capture metadata.
- Analytics: outcome counts and finding counts per system derived from the same loaded cases.

The server adds only operational request metadata to the presentation adapter. Raw email, request text, identity values and evidence paths remain excluded. Audit decisions and remediation order stay unchanged. Live failures, invalid data and empty responses never load demo fixtures; errors remain visible with Retry. Demo mode requires an explicit setting. Refresh preserves a selected case when it still exists and ignores aborted responses.

Checks: `python -m pytest code/tests/test_slack.py`, `npm.cmd test --prefix code/frontend`, and `npm.cmd run build --prefix code/frontend`. The tests cover live loading, all four consumers, malformed/duplicate responses, empty results, network failures and cancellation. Existing Slack HTML report/security tests remain included. Resend's approval and delivery package is unchanged; the Phase 4 email panel uses its secure standard-library adapter rather than mounting the FastAPI router.


## Phase 3: investigation review

Open any real case from Overview or Investigations. The detail-view case selector retains access to all loaded cases and resets the finding focus and active tab when switching cases. Review the workflow claim beside the backend audit status and audit cutoff.

- Findings focus the supplied resource in the existing 3D graph. Empty findings do not imply deletion is complete.
- Actions and Verification retain backend step order and show the required state. Future checks are labeled pending; evidence-cited checks for COMPLETE results are labeled as verification at the audit cutoff.
- Evidence lists the case's evidence IDs, available capture times, related findings and cited steps. Missing metadata is explicitly marked unavailable; no artifact paths or raw evidence are exposed.
- Graph node details include the corresponding findings, citations, recommendations and verification checks. Existing graph rendering and controls remain intact.
- Send Slack report continues to use the existing protected route and private HTML upload workflow. Feedback remains tied to the case sent, including when another case is selected during delivery.
- Email approval is visibly disabled until Member Two supplies the secure adapter. No email API routes or Resend integration have been added.

The requested `code/integrations/email/INTEGRATION_PLAN.md` was absent from this checkout; the existing shared contract and package README were inspected, and the strict email boundary above takes precedence. The engine's CaseAuditResult and the email package are unchanged.

Verification: `npm.cmd test --prefix code/frontend`, `npm.cmd run build --prefix code/frontend`, and `python -m pytest code/tests/test_slack.py`. Check a COMPLETE, INCOMPLETE and NOT_APPLICABLE case in live mode, switch cases after reviewing evidence, and confirm the case header, tabs, graph and communication feedback stay aligned. A real Slack check must include both successful upload/link retrieval and authenticated HTML download; text-only success is not a valid verification.


## Phase 4: per-case authenticated email

The Customer email panel uses the existing `/api/email` routes in `code/server.py`. After configuring the server as described in [Member Two's integration plan](../integrations/email/INTEGRATION_PLAN.md), restart the API and refresh Vite. No token or Resend key belongs in a Vite environment variable.

1. Open a real investigation. Enter an operator login token in the password field and choose **Check operator access**. The server identifies the operator and supplies the allowed recipients. Tokens stay only in component/client memory; they are cleared on page refresh, case change, navigation away or **Clear operator login**. They are never placed in browser storage, URLs, exported case reports or logs.
2. Choose an allowed address, or enter an address at an allowed domain. **Create or open draft** asks the backend to generate customer-safe content from the selected case; duplicate drafts reopen the existing record. Select among the case's emails with **Case email**.
3. Edit and save the subject/body, then **Submit for approval**. Pending and approved content is read-only. Clear the operator login and sign in as a different operator to approve or reject; authors, editors and submitters cannot approve through this UI, even if demo self-approval is enabled on the backend.
4. For an APPROVED record, check the explicit recipient confirmation before **Send approved email**. The server rechecks the content hash and approval. No automatic mutation retries occur. After a rejected draft, edit and re-draft it; a FAILED send must be submitted for approval again.
5. **Refresh email status** fetches current state and audit events. After errors or uncertain sends, refreshing is required before further actions. `SENT` means the provider accepted the send, not verified inbox delivery. The loopback API does not receive Resend delivery webhooks; delivered/bounced events are unavailable unless a separate secure webhook listener is configured outside this UI.

Every email request includes credentials, the current session CSRF token and bearer authorization. The password form is unavailable in demo mode. Backend 401/403/409/429/503 outcomes have fixed, safe messages; server error bodies are not echoed. The frontend remains usable without email configuration, and Slack HTML reporting is independent.

Tests: `npm.cmd test --prefix code/frontend` and `npm.cmd run build --prefix code/frontend`; backend checks are `python -m pytest code/tests`. Email tests use fake transports only, including the send path. Do not enter production tokens or send real emails as part of automated testing.


### Vite port and local API protections

Use `http://localhost:5173` or `http://127.0.0.1:5173` for development, and port 4173 for preview. Both Vite configurations use `strictPort: true`: if a port is occupied, Vite stops instead of silently shifting to 5174. Reuse the existing server or stop the duplicate before restarting. Do not bypass this by overriding the port or widening the backend's origin allowlist.

A page opened on port 5174 sends an untrusted Host (and, when present, Origin) through the unchanged proxy, so `/api/cases` correctly returns 403. This rejection precedes case routing and is unrelated to email bearer authentication. The bearer requirement applies only to `/api/email/*`; Slack still uses its existing session/CSRF checks. Case reads remain available through the trusted local proxy, including with the current session cookie. No authentication or CSRF checks were relaxed.


### Operator login after a token update

Operator credentials are a startup snapshot. `email_operator_token.py --env-file .env` stores a `name:SHA-256-hash` entry; the password field takes the raw one-time login token, not the hash or the `EMAIL_OPERATORS` line. Saving or rotating a token does not reload the running API. Restart the backend, then refresh the frontend and sign in with the already-generated token. Re-generating again would replace the token you just saved.

A 401 from `/api/email/status` means bearer authentication failed. Session/origin/CSRF failures use 403, missing operator/recipient configuration uses 503, and login rate limiting uses 429. Operators have no automatic token expiry; tokens remain valid until replaced. If a shell defines `EMAIL_OPERATORS`, it takes precedence over the root `.env`; clear that shell override before restarting when the root file is intended to be authoritative. Never share the raw token or its stored hash for troubleshooting.
