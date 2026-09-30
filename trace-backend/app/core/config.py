"""
Runtime configuration for the TRACE dashboard integration layer.

Everything here is overridable via environment variables so the same code
runs unchanged in a quick local dev loop (small row cap, fast startup) and
against the full 2.57M-row dataset (no cap, slower startup) in a "real" run.
"""
import os


def _int_env(name, default):
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        parsed = int(val)
        return parsed if parsed > 0 else None
    except ValueError:
        return default


def _float_env(name, default):
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


# Feature config + dataset paths (same defaults train.py/evaluate.py assume).
FEATURE_CONFIG_PATH = os.getenv("TRACE_FEATURE_CONFIG", "configs/feature_config.json")
DATA_PATH = os.getenv("TRACE_DATA_PATH", "data/CIC_IDS2017_PS1_Cleaned.csv")
CHECKPOINT_PATH = os.getenv("TRACE_CHECKPOINT", "checkpoints/world_model.pt")
SCALER_PATH = os.getenv("TRACE_SCALER", "checkpoints/scaler.pkl")

# Cap on rows streamed into the in-memory live engine at startup. The default
# keeps `uvicorn --reload` snappy during development; set TRACE_MAX_ROWS=0
# (or unset the cap) to build the live engine from the entire dataset.
MAX_ROWS = _int_env("TRACE_MAX_ROWS", 300_000)

# How often (seconds) the in-memory "current window" cursor auto-advances,
# simulating a live flow feed over the static dataset. The dashboard polls
# /network/state every 15s, so a smaller tick makes the UI feel like it's
# moving between polls without being frantic.
TICK_SECONDS = _float_env("TRACE_TICK_SECONDS", 5.0)

# Nominal wall-clock duration represented by one aggregation window. The
# dataset has no reliable per-flow timestamps (feature_config.json sets
# timestamp_column to null), so this is only used to *pace* the synthetic
# timestamps shown on the risk-timeline chart -- it is not measured from
# real capture times.
WINDOW_DURATION_SEC = _float_env("TRACE_WINDOW_DURATION_SEC", 5.0)

# Bound on how many flow-level rows are kept in memory for the one-time,
# best-effort performance-metrics computation (logistic-regression baseline)
# shown on the Model page. This is NOT the training set -- it's a small,
# fixed sample evaluated once at startup so the status endpoint has real
# (if approximate) numbers instead of fabricated ones.
EVAL_SAMPLE_ROWS = _int_env("TRACE_EVAL_SAMPLE_ROWS", 20_000)

# How many of the most-recently-streamed flow-level rows to keep in memory
# (a rolling window, oldest evicted first) for the Telemetry page. Kept
# separate from -- and much smaller than -- the aggregated state timeline
# so memory use stays bounded even against the full 2.57M-row dataset.
TELEMETRY_SAMPLE_ROWS = _int_env("TRACE_TELEMETRY_SAMPLE_ROWS", 5_000)

# CORS origins allowed to call this API. Vite's default dev port is 5173.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("TRACE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
