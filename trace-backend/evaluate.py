import argparse
import json

import numpy as np
import torch
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

from app.data.loader import iter_csv_chunks
from app.features.state_builder import build_states_for_file
from app.features.sequences import build_sequences
from app.models.gru_world_model import GRUWorldModel
from app.forecasting.rollout import rollout
from app.forecasting.risk_engine import compute_risk_score


def load_checkpoint(path):
    ckpt = torch.load(path, map_location="cpu")
    model = GRUWorldModel(ckpt["input_size"], ckpt["hidden_size"], ckpt["num_layers"])
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, ckpt


def next_state_mae(model, X, y, batch_size=512):
    maes = []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            xb = torch.tensor(X[i:i + batch_size])
            pred = model(xb).numpy()
            maes.append(np.mean(np.abs(pred - y[i:i + batch_size])))
    return float(np.mean(maes))


def k_step_mae(model, states, seq_len, K, n_samples=200):
    n = len(states) - seq_len - K
    if n <= 0:
        return None
    idxs = np.linspace(0, n - 1, min(n_samples, n)).astype(int)
    maes = []
    for i in idxs:
        history = states[i:i + seq_len]
        true_future = states[i + seq_len:i + seq_len + K]
        preds, _diagnostics = rollout(model, history, K)
        maes.append(np.mean(np.abs(np.array(preds) - np.array(true_future))))
    return float(np.mean(maes))


def logistic_regression_baseline(X_flow, y_binary):
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_flow, y_binary, test_size=0.2, random_state=42,
        stratify=y_binary if len(set(y_binary)) > 1 else None)
    clf = LogisticRegression(max_iter=500)
    clf.fit(X_tr, y_tr)
    pred = clf.predict(X_te)
    proba = clf.predict_proba(X_te)[:, 1]
    return {
        "precision": precision_score(y_te, pred, zero_division=0),
        "recall": recall_score(y_te, pred, zero_division=0),
        "f1": f1_score(y_te, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_te, proba) if len(set(y_te)) > 1 else None,
    }


def reservoir_sample_update(X_sample, y_sample, X_chunk, y_chunk, max_samples, seen, rng):
    """Bound evaluation memory by keeping a uniform reservoir sample."""
    for row, label in zip(X_chunk, y_chunk):
        seen += 1
        if len(X_sample) < max_samples:
            X_sample.append(row.copy())
            y_sample.append(int(label))
        else:
            j = int(rng.integers(0, seen))
            if j < max_samples:
                X_sample[j] = row.copy()
                y_sample[j] = int(label)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--config", default="configs/feature_config.json")
    ap.add_argument("--checkpoint", default="checkpoints/world_model.pt")
    ap.add_argument("--scaler", default="checkpoints/scaler.pkl")
    ap.add_argument("--K", type=int, default=5)
    ap.add_argument("--chunksize", type=int, default=200_000)
    ap.add_argument("--baseline_sample", type=int, default=100_000)
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    feature_cols = cfg["selected_features"]
    std_cols = cfg["state_std_features"]
    label_col = cfg.get("label_column")
    timestamp_col = cfg.get("timestamp_column")

    model, ckpt = load_checkpoint(args.checkpoint)
    scaler = joblib.load(args.scaler)
    seq_len = ckpt["seq_len"]

    all_states, all_metas = [], []
    flow_sample_X, flow_sample_y = [], []
    seen_flows = 0
    rng = np.random.default_rng(42)

    for path in args.data:
        # Stream the file once. States are small (~one state per window), while
        # the flow-level baseline uses a bounded reservoir sample instead of
        # materializing millions of rows in RAM.
        chunks = iter_csv_chunks(path, feature_cols, label_col, timestamp_col, args.chunksize)

        def tracked_chunks():
            nonlocal seen_flows
            for chunk in chunks:
                Xs = scaler.transform(chunk[feature_cols].values).astype("float32")
                if label_col and label_col in chunk.columns:
                    y = (chunk[label_col].astype(str).str.upper() != "BENIGN").astype(int).values
                    seen_flows = reservoir_sample_update(
                        flow_sample_X, flow_sample_y, Xs, y, args.baseline_sample, seen_flows, rng
                    )
                yield chunk

        states, metas = build_states_for_file(
            tracked_chunks(), feature_cols, std_cols, scaler, ckpt["window_size"], label_col
        )
        all_states.extend(states)
        all_metas.extend(metas)
        print(f"  {path}: {len(states)} states")

    print(f"Total evaluation states: {len(all_states)}")

    X_seq, y_seq = build_sequences(all_states, seq_len)
    if len(X_seq) == 0:
        print("Not enough states to build evaluation sequences.")
        return

    print(f"Next-state MAE: {next_state_mae(model, X_seq, y_seq):.5f}")
    kmae = k_step_mae(model, all_states, seq_len, args.K)
    print(f"{args.K}-step rollout MAE: {kmae}")

    if flow_sample_X and len(set(flow_sample_y)) > 1:
        X_flow = np.asarray(flow_sample_X, dtype="float32")
        y_flow = np.asarray(flow_sample_y, dtype=int)
        print(f"Logistic Regression baseline (bounded sample: {len(y_flow):,} / {seen_flows:,} flows):")
        for k, v in logistic_regression_baseline(X_flow, y_flow).items():
            print(f"  {k}: {v}")

    baseline_mean = np.array(ckpt["baseline_mean"])
    baseline_std = np.array(ckpt["baseline_std"])
    active_mask = np.array(ckpt["anomaly_active_mask"]) if "anomaly_active_mask" in ckpt else None
    risk_scores = [compute_risk_score(s, baseline_mean, baseline_std, active_mask) for s in all_states]
    attack_flags = [m["attack_fraction"] is not None and m["attack_fraction"] > 0.5 for m in all_metas]

    if any(attack_flags) and not all(attack_flags):
        threshold = 0.5
        warn_idx = next((i for i, r in enumerate(risk_scores) if r > threshold), None)
        attack_idx = next((i for i, f in enumerate(attack_flags) if f), None)
        if warn_idx is not None and attack_idx is not None and warn_idx <= attack_idx:
            lead = attack_idx - warn_idx
            print(f"Early warning: risk crossed {threshold} at window {warn_idx}, "
                  f"ground-truth attack window at {attack_idx} -> lead = {lead} window(s) "
                  f"({lead * ckpt['window_size']} flows). NOTE: lead time is flow-window index, "
                  "not wall-clock time because this dataset has no Timestamp column.")
        else:
            print("Early warning could not be established (no clean warning-before-attack pattern).")
    else:
        print("Early warning evaluation skipped: no mixed benign/attack transition in this data.")


if __name__ == "__main__":
    main()
