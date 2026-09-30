# TRACE Backend Prototype

A forecasting-based network intrusion early-warning system built on CIC-IDS2017-style
flow data. Instead of classifying individual flows, it compresses windows of flows into
compact "network state" vectors and trains a GRU **world model** to predict future
states, from which a heuristic risk score, attack-stage guess, and feature-level
explanation are derived.

This backend now also powers the `frontend/` React dashboard directly -- see
**"Frontend integration"** below.

**The dashboard integration layer (`app/core/live_engine.py`, `app/api/dashboard_routes.py`,
`app/main.py`'s CORS/router wiring) has been written and traced through carefully against
the real dataset and checkpoint you provided, using the parts of the pipeline that don't
need torch (loader, state builder, risk/stage math) run directly against
`data/CIC_IDS2017_PS1_Cleaned.csv` in the sandbox that built this. The torch-dependent
paths (the GRU model itself, rollout, FastAPI/uvicorn) could not be executed here --
there's no network access to install torch or fastapi in this environment. Run it locally
and paste back any traceback.**

## How dataset-swapping works

Everything dataset-specific lives in `configs/feature_config.json` (label column,
timestamp column, selected feature columns). The loader/state-builder/train/evaluate
scripts never hardcode column names. To point at the real CIC-IDS2017 files:
overwrite/replace `data/sample_cicids2017.csv` or pass new paths via `--data`
(multiple files supported, since CIC-IDS2017 ships as 8 daily CSVs — each file is
windowed into states separately so attack/benign transitions don't leak across days).
Leading/trailing whitespace in column headers is auto-stripped.

## Running it

```bash
pip install -r requirements.txt

# 1. sanity-check the whole pipeline on tiny synthetic data
python tests/test_pipeline.py

# 2. generate a demo dataset and train (DEMO MODE)
python scripts/generate_sample_data.py --n_rows 20000 --out data/sample_cicids2017.csv
python train.py --mode demo --data data/sample_cicids2017.csv

# 3. evaluate
python evaluate.py --data data/sample_cicids2017.csv

# 4. once you have the REAL CIC-IDS2017 CSV(s):
python scripts/inspect_dataset.py --path /path/to/real_day1.csv
# edit configs/feature_config.json only if column names differ
python train.py --mode full --data /path/real_day1.csv /path/real_day2.csv ... --chunksize 200000

# 5. serve
uvicorn app.main:app --reload
curl http://localhost:8000/health
curl -X POST http://localhost:8000/forecast -H "Content-Type: application/json" \
  -d '{"state_history": [[...41 numbers...], ... x20], "K": 5}'
```

## Directory structure

```
trace-backend/
├── app/
│   ├── api/routes.py            # FastAPI endpoints: /health, /model/status, /forecast, /rollout, /explain
│   ├── core/config.py, schemas.py, model_registry.py
│   ├── data/loader.py           # streaming CSV loader/cleaner
│   ├── features/preprocessing.py, state_builder.py, sequences.py
│   ├── models/gru_world_model.py
│   ├── forecasting/rollout.py, risk_engine.py, stage_mapper.py
│   ├── explainability/perturbation.py
│   └── main.py
├── configs/feature_config.json  # the only file you touch when changing datasets
├── scripts/generate_sample_data.py, inspect_dataset.py
├── tests/test_pipeline.py
├── train.py
├── evaluate.py
└── requirements.txt
```

## Known, deliberate simplifications (not bugs)

- Trailing partial windows smaller than `window_size` are dropped.
- `risk_score` (in `risk_engine.py`) is an explicit heuristic — anomaly z-scores
  squashed into [0,1] via `1 - e^(-alpha*x)`. It is **not a calibrated probability**;
  no calibration step has been implemented.
- Stage mapping (`stage_mapper.py`) is rule-based and illustrative, not scientifically
  validated. `evaluate.py`'s `LABEL_TO_STAGE_GROUND_TRUTH` dict is the separate, honest
  ground-truth mapping used only for scoring.
- Early-warning lead time (in `evaluate.py`) is measured in "windows of flows," not
  wall-clock time, unless the dataset's timestamps have been independently verified as
  real capture times.
- `evaluate.py` holds one pass of cleaned, scaled flow-level features in memory for the
  logistic-regression baseline (~300MB even at 2.7M rows — fine on 8GB RAM). Training
  itself never does this; it only ever holds compact state vectors.
- `scripts/generate_sample_data.py` produces a synthetic placeholder matching the real
  CICFlowMeter column schema, with attacks in contiguous bursts (not scattered) so the
  early-warning check has something meaningful to detect. Results from this synthetic
  data are for pipeline validation only, not security findings.


## Real CIC-IDS2017 cleaned dataset

This package is prepared for the cleaned dataset used with TRACE. Place the CSV at:
`data/CIC_IDS2017_PS1_Cleaned.csv`

The configuration uses `Label` as metadata and does not use `_source_file` as a model feature. This dataset has no `Timestamp` column, so `timestamp_column` is intentionally set to `null`.

Before full training:
```powershell
python scripts/inspect_dataset.py --path data/CIC_IDS2017_PS1_Cleaned.csv
python train.py --mode full --data data/CIC_IDS2017_PS1_Cleaned.csv
```

After training:
```powershell
python evaluate.py --data data/CIC_IDS2017_PS1_Cleaned.csv
uvicorn app.main:app --reload
```

The evaluation script uses a bounded 100,000-flow reservoir sample for the logistic-regression baseline so evaluation does not materialize the full multi-million-row dataset in memory.

## Frontend integration

`app/main.py` now mounts two routers:
- The original core ML API (`/health`, `POST /forecast|/rollout|/explain`,
  `GET /model/status/internal`) -- unchanged behavior, just moved off `/model/status`
  to make room for the dashboard's version of that path.
- A new dashboard API under `/api/*` (`app/api/dashboard_routes.py`), shaped exactly to
  match `frontend/src/utils/mockData.js`'s contracts (`NetworkState`, `Forecast`,
  `RiskTimeline`, `AttackStage`, `AttackPath`, `TelemetryFlow`, `Explanation`,
  `Incident`, `ModelStatus`).

### How it works

`app/core/live_engine.py` streams the dataset **once** at startup and builds the same
aggregated "state" timeline train.py/evaluate.py use, plus a rolling sample of
individual flows for the Telemetry page. A background task then advances a cursor over
that timeline every `TRACE_TICK_SECONDS` (default 5s), so the dashboard's polling
(every 15-30s per page, see `frontend/src/hooks/`) sees the "current window" move --
simulating a live feed over a recorded dataset, since CIC-IDS2017 is static.

### Running both together

```bash
# Terminal 1 -- backend
cd trace-backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# First startup streams the dataset and builds the live engine -- can take from several
# seconds to a couple of minutes depending on TRACE_MAX_ROWS (see below). Endpoints
# under /api/* return 503 with a reason until it finishes.

# Terminal 2 -- frontend
cd frontend
npm install
npm run dev
# Opens http://localhost:5173. frontend/.env already points it at
# http://localhost:8000/api with VITE_DEMO_MODE=false.
```

To go back to mock data at any time, set `VITE_DEMO_MODE=true` in `frontend/.env` (or
delete the file) -- no other change needed.

### Config knobs (env vars, all optional)

| Variable | Default | Purpose |
|---|---|---|
| `TRACE_DATA_PATH` | `data/CIC_IDS2017_PS1_Cleaned.csv` | dataset the live engine streams |
| `TRACE_MAX_ROWS` | `300000` | cap on rows loaded at startup, for fast dev; `0` = full 2.57M-row file |
| `TRACE_TICK_SECONDS` | `5` | how often the "current window" cursor auto-advances |
| `TRACE_WINDOW_DURATION_SEC` | `5` | nominal seconds per window, used only to pace synthetic timestamps |
| `TRACE_EVAL_SAMPLE_ROWS` | `20000` | bounded sample for the one-time Model-page performance metrics |
| `TRACE_TELEMETRY_SAMPLE_ROWS` | `5000` | rolling per-flow sample kept in memory for the Telemetry page |
| `TRACE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | comma-separated allowed origins |

### What's real vs. placeholder in this integration

Everything numeric that touches the model -- risk scores, stage predictions, K-step
forecasts, explanations, evaluation metrics -- is computed the same way `evaluate.py`
computes it, from the real dataset and the real checkpoint. Two things the *dashboard's
contract* expects that the *dataset* genuinely doesn't contain are filled in honestly
rather than silently faked:

- **Attack Path topology.** The cleaned CSV has no source/destination IP columns, so
  there's no real host graph to reconstruct. `GET /network/attack-path` returns a
  minimal, clearly-commented 3-node chain (External Traffic → Network Perimeter →
  Monitored Segment) driven by the real current risk/stage, not a fabricated multi-host
  network. If you get a version of CIC-IDS2017 with IPs, this is the one endpoint worth
  rewriting for a real topology.
- **Telemetry row identifiers.** The CSV has no source IP, source port, or protocol
  columns (only `Destination Port` is real). `GET /telemetry` fills `sourceIp`,
  `destinationIp`, `sourcePort`, and `protocol` with deterministic, clearly-labeled
  placeholders (see `_synthetic_identity` in `dashboard_routes.py`) so the table is
  browsable; risk score, stage, packet/byte counts, and destination port are real,
  per-flow, model-consistent values.
- **Affected hosts on Incidents** are left as an empty list for the same reason (no host
  identity in the data) rather than invented IPs.
- **Lead time / timeline timestamps** reuse the same "index-based, not wall-clock"
  caveat already documented above for `evaluate.py` -- there's no verified per-flow
  timestamp column, so seconds shown are windows × a nominal `TRACE_WINDOW_DURATION_SEC`.

The Model page's evaluation metrics (F1/precision/recall/ROC-AUC, K-step error) are
computed once at startup against a bounded sample (`TRACE_EVAL_SAMPLE_ROWS`), not the
full corpus, so the server starts in seconds rather than minutes; if that computation
fails for any reason, the fields come back `null` rather than a fabricated number.

MITRE ATT&CK mapping (`MitrePanel` on the Explainability page) is intentionally left
wired to its existing static illustrative table -- the model has no real MITRE
technique inference to serve there.

### Known frontend-side quirk (not fixed here, cosmetic)

`frontend/src/pages/ForecastPage.jsx` has a hardcoded `"Lead Time: +18 sec"` metric card
that was never wired to `useModelStatus()` -- it's static demo text left over from
scaffolding, not fetched data, so it won't reflect the real `leadTimeSec` value now
available from `/api/model/status`. Harmless, but worth wiring up if you want that card
to be live.
