# EraSight frontend — Member One

React, TypeScript, Vite, Tailwind CSS, Cytoscape.js, Recharts and lightweight custom components. Requires Node 22 or later.

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

The default is a clearly labeled demonstration workspace with six fictional cases, including complete and incomplete outcomes. Navigation, search, result filters, case selection, graph zoom/pan, node inspection, finding-path highlighting, recommended actions, evidence capture history, analytics, and per-case JSON download work locally. The canvas has a keyboard-accessible node list. No graph relationship is inferred from live data.

To use Member Two's results, copy `.env.example` to `.env.local`, set `VITE_DATA_MODE=live`, set the API base URL and restart Vite. See [CONTRACT.md](./CONTRACT.md). Live API failures remain visible with Retry. The API, Slack webhook, email routes and final challenge-output validation belong to subsequent integration milestones; communication controls accurately show that these are not connected.

Never set webhook URLs or provider keys in a `VITE_` variable: those values are public browser configuration. This frontend does not alter the dataset, engine, or challenge `output.csv`.
