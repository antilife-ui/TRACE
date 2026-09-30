# TRACE — Frontend

AI World Model command interface for network attack forecasting (SIH26153).
React + Vite + Tailwind, built to the TRACE frontend spec.

## Run it

```bash
npm install
npm run dev
```

Opens on http://localhost:5173. It runs entirely on mock data out of the
box — no backend required to see every page.

## Connect your real backend

1. Copy `.env.example` to `.env`.
2. Set `VITE_API_BASE_URL` to your backend's base URL.
3. Set `VITE_DEMO_MODE=false`.
4. In each file under `src/api/`, delete the mock branch (`if (DEMO_MODE) ...`)
   — the real `fetch` call below it is already written to the contract
   shape documented in the original spec. If your backend's field names
   differ, adapt the `apiGet(...)` call in that one file; no component or
   page needs to change, because everything downstream consumes the
   hook, not the endpoint.

Example, in `src/api/networkApi.js`:

```js
export async function fetchNetworkState() {
  if (DEMO_MODE) return mockDelay(generateNetworkState());
  return apiGet('/network/state');
}
```

Delete the `if (DEMO_MODE)` line once you're pointed at a real backend, or
just leave `VITE_DEMO_MODE=false` and it'll skip straight to the real call.

## Structure

```
src/
  api/          one file per backend resource — the only place that knows
                about endpoints. Swap mock <-> real here, nowhere else.
  hooks/        useNetworkState, useForecast, useTelemetry, etc. — wrap
                api/ calls with loading/error/refresh state and polling.
  components/
    layout/     CyberShell, TopBar, Sidebar — the app chrome
    common/     Panel, MetricCard, StatusBadge, SectionHeader, loading/
                error/empty states — reused on every page
    network/    NetworkGraph (SVG) + its layout algorithm
    forecast/   RiskForecastChart, AttackProgressionTimeline,
                FutureStateTimeline (the K-step World Model view)
    telemetry/  TelemetryTable
    explainability/  ExplanationPanel, MitrePanel
    model/      KStepErrorChart
  pages/        one file per nav item — Overview, Network, Forecast,
                AttackPath, Telemetry, Explainability, Incidents, Model
  utils/
    mockData.js    generators matching every contract shape from the spec
    formatters.js  formatPercent, formatBytes, riskLevel, etc.
```

## What's real vs. simplified in this scaffold

- **Data contracts** — every mock object in `utils/mockData.js` matches
  the field names and shapes in the spec (`NetworkState`, `Forecast`,
  `RiskTimeline`, `AttackStage`, `AttackPath`, `TelemetryFlow`,
  `Explanation`, `Incident`, `ModelStatus`). Point `api/` at a real
  backend that returns these shapes and the UI needs no changes.
- **Network graph layout** — uses a simple BFS-depth layered layout
  (`components/network/graphLayout.js`), which is right for the
  shallow attacker → gateway → hosts → target chains this product
  deals with. If your backend starts returning large, densely
  connected graphs, swap this for a force-directed layout (e.g. d3-force)
  — the `NetworkGraph` component's node/edge rendering doesn't need to
  change, only the positions it's given.
- **Telemetry pagination** — paginates real mock data (25 rows/page)
  rather than true virtualization. Fine at this scale; if the backend
  starts returning very large pages, add `react-window` inside
  `TelemetryTable` — the filter/pagination contract in `useTelemetry`
  already assumes server-side filtering, so no rework needed there.
- **MITRE mapping** (`MitrePanel`) — currently a static illustrative
  table. Wire it to a real `/explanations/mitre`-style endpoint the
  same way every other panel is wired, once your backend produces
  tactic/technique inferences.
- **Observed vs. predicted** — enforced visually everywhere (solid vs.
  dashed lines, cyan vs. violet color, explicit status badges) and in
  the data shapes (`kind: 'observed' | 'predicted'`, `status: 'observed'
  | 'current' | 'predicted' | 'inferred'`). Keep that field on every
  real response — several components branch on it directly.

## Design tokens

Colors, fonts, and animation keyframes live in `tailwind.config.js`.
Cyan (`accent`) = analytical/observed, violet (`predicted`) = model
forecast, amber (`warning`), red (`critical`), green (`healthy`) — never
used alone; every status also carries an icon and a text label
(`StatusBadge`).
