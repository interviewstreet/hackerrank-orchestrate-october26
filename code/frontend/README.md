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

The default is a clearly labeled demonstration workspace with six fictional cases, including complete and incomplete outcomes. Navigation, search, result filters, case selection, 3D globe rotation/zoom, node inspection, finding-path highlighting, recommended actions, evidence capture history, analytics, and per-case JSON download work locally. The canvas has a keyboard-accessible node list. No graph relationship is inferred from live data.

To use Member Two's results, copy `.env.example` to `.env.local`, set `VITE_DATA_MODE=live`, set the API base URL and restart Vite. See [CONTRACT.md](./CONTRACT.md). Live API failures remain visible with Retry. The local presentation API and Slack route are available through code/server.py. Slack delivery requires live engine data; demo sends are disabled. Email routes remain a separate Member Two integration milestone.

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
