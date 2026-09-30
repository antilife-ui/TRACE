"""
LiveEngine turns the static CIC-IDS2017 CSV into something a live dashboard
can poll: it streams the file once at startup, builds the same aggregated
"state" vectors train.py/evaluate.py use, and keeps a moving cursor over
them that auto-advances on a timer -- simulating a live flow feed over a
recorded dataset.

This module deliberately does NOT modify app/features/state_builder.py: it
re-implements the same windowing logic locally so it can also capture a
few raw (unscaled) per-window aggregates -- packet/byte totals, dominant
label -- that the dashboard needs for display but the training pipeline
never required. Forecasting/risk/stage logic itself is delegated to the
existing app.forecasting modules, so scores here are computed the same way
evaluate.py computes them.

Known, deliberate simplifications (mirrors the ones documented in the main
README):
  - Only TRACE_MAX_ROWS rows (default 300,000) are loaded by default for a
    fast dev startup; set TRACE_MAX_ROWS=0 to use the full 2.57M-row file.
  - The dataset has no reliable per-flow timestamps, so timeline timestamps
    are synthetically paced using TRACE_WINDOW_DURATION_SEC, not measured.
  - The dataset carries no source/destination IPs, so the "attack path"
    view cannot reconstruct real host topology -- see dashboard_routes.py.
  - Performance metrics (Model page) are computed once at startup against a
    bounded sample (TRACE_EVAL_SAMPLE_ROWS), not the full corpus, so the
    server starts in seconds rather than minutes. If that computation
    fails for any reason, `performance` is reported as null rather than a
    fabricated number.
"""
import asyncio
import json
import os
import threading
import time
from collections import deque

import numpy as np

from app.core import config as cfg
from app.core.model_registry import registry
from app.forecasting.risk_engine import compute_risk_score
from app.forecasting.rollout import rollout
from app.forecasting.stage_mapper import build_feature_groups, predict_stage

# "Destination Port" is a real column in the raw CSV but is NOT one of the model's
# selected_features (see configs/feature_config.json), so the shared iter_csv_chunks
# loader -- which only keeps feature_cols + label/timestamp -- drops it. It's the one
# genuinely real per-flow identifier the dataset has, so we keep it around separately
# for telemetry display via the local chunk reader below instead of fabricating it too.
EXTRA_DISPLAY_COLUMNS = ["Destination Port"]


def _iter_chunks_with_extra(path, feature_cols, label_col, timestamp_col, extra_cols, chunksize=200_000):
    """Same row-cleaning as app.data.loader.clean_chunk, but keeps `extra_cols`
    (columns present in the file that aren't model input features) alongside the
    feature columns from the start, so they stay correctly aligned through the
    same dropna/dtype pass rather than needing to be re-attached afterwards."""
    import pandas as pd

    reader = pd.read_csv(path, chunksize=chunksize, low_memory=False)
    for raw_chunk in reader:
        raw_chunk.columns = [c.strip() for c in raw_chunk.columns]

        missing = [c for c in feature_cols if c not in raw_chunk.columns]
        if missing:
            raise ValueError(f"Missing expected feature columns: {missing}")

        cols_needed = list(feature_cols)
        if label_col and label_col in raw_chunk.columns:
            cols_needed.append(label_col)
        if timestamp_col and timestamp_col in raw_chunk.columns:
            cols_needed.append(timestamp_col)
        present_extra = [c for c in extra_cols if c in raw_chunk.columns and c not in cols_needed]
        cols_needed += present_extra

        df = raw_chunk[cols_needed].copy()
        for c in feature_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=feature_cols)
        df[feature_cols] = df[feature_cols].astype("float32")
        for c in present_extra:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        if len(df) > 0:
            yield df.reset_index(drop=True)


class LiveEngine:
    def __init__(self):
        self.ready = False
        self.error = None

        self.states = []   # list[np.ndarray] -- scaled state vectors, same layout as training
        self.metas = []    # list[dict] -- dominant_label, attack_fraction, total_packets, total_bytes, avg_dst_port
        self.flow_sample = deque(maxlen=cfg.TELEMETRY_SAMPLE_ROWS)  # rolling per-flow sample, for Telemetry page

        self.cursor = 0
        self.seq_len = None
        self.window_size = None
        self.feature_cols = None
        self.std_cols = None
        self.state_feature_names = None
        self.baseline_mean = None
        self.baseline_std = None
        self.anomaly_active_mask = None
        self.groups = None

        self.dataset_name = None
        self.dataset_path = None
        self.total_rows_seen = 0
        self.max_rows_capped = False

        self.performance = None  # filled in by _compute_performance(), or left None on failure
        self.flow_zero_baseline = None
        self.flow_one_baseline = None

        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def build(self):
        if not registry.loaded:
            self.error = "model checkpoint not loaded (run train.py first)"
            print(f"[live-engine] {self.error}; live engine disabled.")
            return

        if not os.path.exists(cfg.DATA_PATH):
            self.error = f"dataset not found at {cfg.DATA_PATH}"
            print(f"[live-engine] {self.error}; live engine disabled.")
            return

        ckpt = registry.config
        self.seq_len = ckpt["seq_len"]
        self.window_size = ckpt["window_size"]
        self.feature_cols = ckpt["selected_features"]
        self.std_cols = ckpt["state_std_features"]
        self.state_feature_names = ckpt["state_feature_names"]
        self.baseline_mean = np.array(ckpt["baseline_mean"])
        self.baseline_std = np.array(ckpt["baseline_std"])
        # None for a checkpoint trained before this mask existed -- compute_risk_score /
        # predict_stage fall back to deriving it from baseline_std at call time.
        self.anomaly_active_mask = (
            np.array(ckpt["anomaly_active_mask"]) if "anomaly_active_mask" in ckpt else None
        )
        self.groups = build_feature_groups(self.feature_cols)

        with open(cfg.FEATURE_CONFIG_PATH) as f:
            fcfg = json.load(f)
        label_col = fcfg.get("label_column")
        timestamp_col = fcfg.get("timestamp_column")

        self.dataset_name = os.path.basename(cfg.DATA_PATH)
        self.dataset_path = cfg.DATA_PATH

        scaler = registry.scaler
        std_idx = [self.feature_cols.index(c) for c in self.std_cols]
        pkt_cols = [c for c in ("Total Fwd Packets", "Total Backward Packets") if c in self.feature_cols]
        byte_cols = [c for c in ("Total Length of Fwd Packets", "Total Length of Bwd Packets")
                     if c in self.feature_cols]
        flowdur_idx = self.feature_cols.index("Flow Duration") if "Flow Duration" in self.feature_cols else None
        pkt_idx = [self.feature_cols.index(c) for c in pkt_cols]
        byte_idx = [self.feature_cols.index(c) for c in byte_cols]
        # A scaler-standardized flow vector is already ~mean-0/std-1 over the training
        # distribution, so the same anomaly heuristic used at state-level applies at
        # flow-level with a zero/one baseline -- no separate flow-level baseline needed.
        self.flow_zero_baseline = np.zeros(len(self.feature_cols))
        self.flow_one_baseline = np.ones(len(self.feature_cols))

        max_rows = cfg.MAX_ROWS
        eval_cap = cfg.EVAL_SAMPLE_ROWS
        eval_X, eval_y = [], []

        buffer_X, buffer_labels, buffer_raw, buffer_dst_port = [], [], [], []
        rows_read = 0
        t0 = time.time()

        try:
            for chunk in _iter_chunks_with_extra(cfg.DATA_PATH, self.feature_cols, label_col, timestamp_col,
                                                  EXTRA_DISPLAY_COLUMNS, chunksize=200_000):
                if max_rows and rows_read >= max_rows:
                    self.max_rows_capped = True
                    break

                X = scaler.transform(chunk[self.feature_cols].values).astype("float32")
                raw = chunk[self.feature_cols].values.astype("float32")
                labels = chunk[label_col].values if (label_col and label_col in chunk.columns) else None
                dst_port_vals = (chunk["Destination Port"].values.astype("float32")
                                 if "Destination Port" in chunk.columns else None)

                if labels is not None and len(eval_X) < eval_cap:
                    take = min(eval_cap - len(eval_X), len(chunk))
                    eval_X.append(X[:take])
                    eval_y.append((chunk[label_col].astype(str).values[:take] != "BENIGN").astype(int))

                for i in range(len(chunk)):
                    if max_rows and rows_read >= max_rows:
                        self.max_rows_capped = True
                        break

                    buffer_X.append(X[i])
                    buffer_raw.append(raw[i])
                    if labels is not None:
                        buffer_labels.append(labels[i])
                    dst_port_val = float(dst_port_vals[i]) if dst_port_vals is not None else None
                    buffer_dst_port.append(dst_port_val)

                    # Only the raw fields + scaled vector are stored here; risk/stage for a
                    # flow are cheap to compute and are done on-demand per requested page
                    # (see dashboard_routes.flow_risk_and_stage), not for every streamed row.
                    self.flow_sample.append({
                        "index": rows_read,
                        "destPort": dst_port_val,
                        "flowDurationMs": float(raw[i][flowdur_idx]) / 1000.0 if flowdur_idx is not None else None,
                        "packets": int(sum(raw[i][j] for j in pkt_idx)) if pkt_idx else None,
                        "bytes": int(sum(raw[i][j] for j in byte_idx)) if byte_idx else None,
                        "label": str(labels[i]) if labels is not None else None,
                        "vector": X[i],
                    })
                    rows_read += 1

                    if len(buffer_X) == self.window_size:
                        self._flush_window(buffer_X, buffer_labels, buffer_raw, buffer_dst_port, std_idx,
                                            pkt_cols, byte_cols)
                        buffer_X, buffer_labels, buffer_raw, buffer_dst_port = [], [], [], []

                if max_rows and rows_read >= max_rows:
                    break
        except Exception as exc:  # dataset issues shouldn't take the whole API down
            self.error = f"failed while streaming dataset: {exc}"
            print(f"[live-engine] {self.error}")
            return

        self.total_rows_seen = rows_read

        if len(self.states) <= self.seq_len:
            self.error = (f"only {len(self.states)} states built from {rows_read} rows "
                           f"(need > seq_len={self.seq_len}); try raising TRACE_MAX_ROWS")
            print(f"[live-engine] {self.error}")
            return

        self.cursor = self.seq_len - 1  # first index with a full seq_len of history behind it
        self.ready = True
        elapsed = time.time() - t0
        print(f"[live-engine] built {len(self.states)} states from {rows_read} rows "
              f"({self.dataset_name}) in {elapsed:.1f}s; cursor starts at {self.cursor}")

        self._compute_performance(eval_X, eval_y)

    def _flush_window(self, buffer_X, buffer_labels, buffer_raw, buffer_dst_port, std_idx, pkt_cols, byte_cols):
        arr = np.array(buffer_X, dtype="float32")
        raw_arr = np.array(buffer_raw, dtype="float32")
        mean_vec = arr.mean(axis=0)
        std_vec = arr[:, std_idx].std(axis=0)
        flow_count = np.array([self.window_size], dtype="float32")
        state_vec = np.concatenate([mean_vec, std_vec, flow_count])
        self.states.append(state_vec)

        meta = {"flow_count": self.window_size}
        if buffer_labels:
            vals, counts = np.unique(buffer_labels, return_counts=True)
            meta["dominant_label"] = str(vals[np.argmax(counts)])
            meta["attack_fraction"] = float(np.mean([str(l) != "BENIGN" for l in buffer_labels]))
        else:
            meta["dominant_label"], meta["attack_fraction"] = None, None

        def raw_sum(cols):
            total = 0.0
            for c in cols:
                idx = self.feature_cols.index(c)
                total += float(raw_arr[:, idx].sum())
            return total

        meta["total_packets"] = int(raw_sum(pkt_cols)) if pkt_cols else None
        meta["total_bytes"] = int(raw_sum(byte_cols)) if byte_cols else None
        valid_ports = [p for p in buffer_dst_port if p is not None]
        meta["avg_dst_port"] = float(np.mean(valid_ports)) if valid_ports else None

        # Raw (unscaled) means of a couple of representative features, kept purely for
        # honest display on the Network page -- the state vector itself only ever holds
        # scaler-standardized values, which would be misleading to show as "flows/sec".
        for display_name, col_name in (("raw_flow_rate_mean", "Flow Packets/s"),
                                        ("raw_iat_mean", "Flow IAT Mean")):
            if col_name in self.feature_cols:
                idx = self.feature_cols.index(col_name)
                meta[display_name] = float(raw_arr[:, idx].mean())
            else:
                meta[display_name] = None

        self.metas.append(meta)

    def _compute_performance(self, eval_X, eval_y):
        """Best-effort, real (not fabricated) performance snapshot computed once at
        startup against a bounded sample. Any failure leaves self.performance = None."""
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
            import torch

            model = registry.model

            # Next-state MAE + a small K-step rollout MAE, over the states we built.
            from app.features.sequences import build_sequences
            X_seq, y_seq = build_sequences(self.states, self.seq_len)
            next_mae = None
            k_step = []
            if len(X_seq) > 0:
                with torch.no_grad():
                    pred = model(torch.tensor(X_seq)).numpy()
                next_mae = float(np.mean(np.abs(pred - y_seq)))

                n = len(self.states) - self.seq_len - 5
                if n > 0:
                    sample_idxs = np.linspace(0, n - 1, min(30, n)).astype(int)
                    for K in range(1, 6):
                        maes = []
                        for i in sample_idxs:
                            history = self.states[i:i + self.seq_len]
                            true_future = self.states[i + self.seq_len:i + self.seq_len + K]
                            preds, _diagnostics = rollout(model, history, K)
                            maes.append(np.mean(np.abs(np.array(preds) - np.array(true_future))))
                        k_step.append({"horizon": K, "error": round(float(np.mean(maes)), 4)})

            # Flow-level logistic-regression baseline on the bounded sample.
            precision = recall = f1 = roc_auc = None
            if eval_X and eval_y:
                X_flow = np.concatenate(eval_X, axis=0)
                y_flow = np.concatenate(eval_y, axis=0)
                if len(set(y_flow)) > 1:
                    X_tr, X_te, y_tr, y_te = train_test_split(
                        X_flow, y_flow, test_size=0.2, random_state=42, stratify=y_flow)
                    clf = LogisticRegression(max_iter=500)
                    clf.fit(X_tr, y_tr)
                    pred = clf.predict(X_te)
                    proba = clf.predict_proba(X_te)[:, 1]
                    precision = round(float(precision_score(y_te, pred, zero_division=0)), 3)
                    recall = round(float(recall_score(y_te, pred, zero_division=0)), 3)
                    f1 = round(float(f1_score(y_te, pred, zero_division=0)), 3)
                    roc_auc = round(float(roc_auc_score(y_te, proba)), 3)

            # Rough inference latency: time one single-sequence forward pass.
            latency_ms = None
            if len(self.states) > self.seq_len:
                sample = self.states[-self.seq_len:]
                t0 = time.time()
                with torch.no_grad():
                    model(torch.tensor(np.array(sample, dtype="float32")[None]))
                latency_ms = round((time.time() - t0) * 1000, 1)

            # Early-warning lead time, same method as evaluate.py: how many windows
            # before the ground-truth attack window did risk first cross 0.5? This is
            # converted to a nominal number of seconds via WINDOW_DURATION_SEC since
            # the dataset has no verified real timestamps -- it's an approximation
            # consistent with the "index-based, not wall-clock" caveat documented
            # throughout this project, not a new fabrication.
            lead_time_sec = None
            risk_scores_all = [compute_risk_score(s, self.baseline_mean, self.baseline_std, self.anomaly_active_mask)
                                for s in self.states]
            attack_flags = [m.get("attack_fraction") is not None and m["attack_fraction"] > 0.5 for m in self.metas]
            if any(attack_flags) and not all(attack_flags):
                warn_idx = next((i for i, r in enumerate(risk_scores_all) if r > 0.5), None)
                attack_idx = next((i for i, f in enumerate(attack_flags) if f), None)
                if warn_idx is not None and attack_idx is not None and warn_idx <= attack_idx:
                    lead_time_sec = round((attack_idx - warn_idx) * cfg.WINDOW_DURATION_SEC, 1)

            self.performance = {
                "f1": f1,
                "precision": precision,
                "recall": recall,
                "rocAuc": roc_auc,
                "nextStateMae": round(next_mae, 4) if next_mae is not None else None,
                "kStepError": k_step,
                "inferenceLatencyMs": latency_ms,
                "leadTimeSec": lead_time_sec,
                "evalSampleRows": int(sum(len(a) for a in eval_y)) if eval_y else 0,
            }
        except Exception as exc:
            print(f"[live-engine] performance computation skipped: {exc}")
            self.performance = None

    # ------------------------------------------------------------------ #
    # Live cursor
    # ------------------------------------------------------------------ #
    def advance(self):
        if not self.ready:
            return
        with self._lock:
            self.cursor += 1
            if self.cursor >= len(self.states):
                self.cursor = self.seq_len - 1  # loop back once the recording is exhausted

    def history(self, end_index=None):
        """Last seq_len states ending at (and including) end_index, as plain lists."""
        end = self.cursor if end_index is None else end_index
        start = end - self.seq_len + 1
        return [s.tolist() for s in self.states[start:end + 1]]

    def risk_at(self, index):
        return compute_risk_score(self.states[index], self.baseline_mean, self.baseline_std,
                                   self.anomaly_active_mask)

    def stage_at(self, index):
        name, _ = predict_stage(self.states[index], self.baseline_mean, self.baseline_std, self.groups,
                                 self.anomaly_active_mask)
        return name

    def window_id(self, index=None):
        i = self.cursor if index is None else index
        return f"window-{i}"

    def flow_risk_and_stage(self, scaled_vector):
        """Per-flow risk/stage, computed on demand for whatever page of the Telemetry
        table is actually requested (not for every row streamed at startup)."""
        risk = compute_risk_score(scaled_vector, self.flow_zero_baseline, self.flow_one_baseline)
        stage, _ = predict_stage(scaled_vector, self.flow_zero_baseline, self.flow_one_baseline, self.groups)
        return risk, stage


engine = LiveEngine()


async def start_ticker():
    """Background task: auto-advances the live cursor every TICK_SECONDS."""
    while True:
        await asyncio.sleep(cfg.TICK_SECONDS)
        engine.advance()
