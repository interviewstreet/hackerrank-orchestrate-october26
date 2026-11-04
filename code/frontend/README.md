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

To use Member Two's results, copy `.env.example` to `.env.local`, set `VITE_DATA_MODE=live`, set the API base URL and restart Vite. See [CONTRACT.md](./CONTRACT.md). Live API failures remain visible with Retry. The API, Slack webhook, email routes and final challenge-output validation belong to subsequent integration milestones; communication controls accurately show that these are not connected.

Never set webhook URLs or provider keys in a `VITE_` variable: those values are public browser configuration. This frontend does not alter the dataset, engine, or challenge `output.csv`.

## Creative redesign

The overview uses a rounded white studio frame, smaller sentence-case system typography and circular #007BFF light exposure. The globe renders every supplied node with an instanced mesh; edges use the supplied relationships only. A fixed spherical rim and depth layers preserve the silhouette. A separate non-interactive light scaffold adds visual density; it is not counted as evidence and disappears during path inspection. Find a node explains this distinction. Six fictional fixture cases remain clearly labeled. No new analytical results were created for this redesign.

Click a node or choose it from **Find a node** to inspect its findings, evidence references and ordered recommended actions. Controls support rotation, zoom, reset, alert filtering and animation pause. Search and system/type filters are available in the node browser. Reduced-motion preferences disable idle rotation, pulse, exposure animation and moving transitions. Offscreen and hidden-tab globes stop their continuous render loop.

Three.js is loaded as a separate chunk. The renderer uses adaptive pixel ratio and a static SVG projection plus the same keyboard-accessible node browser if WebGL2 is unavailable or the context is lost. The existing case-result API contract remains unchanged.

The current implementation was compared with the inline IMAGE B at its 1800 x 873 viewport. See DESIGN.md for measured corrections and screenshot locations. Resting desktop graph controls appear on hover or keyboard focus; mobile controls stay visible.
