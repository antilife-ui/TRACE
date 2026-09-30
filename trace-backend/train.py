import argparse
import json
import os
import time

import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader
import joblib

from app.data.loader import iter_csv_chunks
from app.features.preprocessing import fit_scaler_streaming, count_cleaned_rows
from app.features.state_builder import build_states_for_file, get_state_feature_names
from app.features.sequences import build_sequences
from app.models.gru_world_model import GRUWorldModel
from app.forecasting.zscore import derive_active_mask

# Single source of truth for the train/val split fraction, applied at BOTH
# the raw-row level (restricting what the scaler ever sees, chronologically)
# and the sequence level below (train_loader/val_loader, baseline stats).
# Keeping both splits at the same fraction and same chronological order
# means "the scaler was fit on train-only rows" and "baseline stats were
# computed on train-only sequences" refer to the same boundary.
TRAIN_FRACTION = 0.85


def load_feature_config(path):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["demo", "full"], default="demo")
    ap.add_argument("--data", nargs="+", required=True, help="one or more CSV files")
    ap.add_argument("--config", default="configs/feature_config.json")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--seq_len", type=int, default=20)
    ap.add_argument("--window_size", type=int, default=100)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--chunksize", type=int, default=200_000)
    ap.add_argument("--hidden_size", type=int, default=128)
    ap.add_argument("--num_layers", type=int, default=1)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--checkpoint_dir", default="checkpoints")
    args = ap.parse_args()

    epochs = args.epochs or (5 if args.mode == "demo" else 20)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"=== TRACE TRAINING [{args.mode.upper()} MODE] === device={device}")

    cfg = load_feature_config(args.config)
    feature_cols = cfg["selected_features"]
    std_cols = cfg["state_std_features"]
    label_col = cfg.get("label_column")
    timestamp_col = cfg.get("timestamp_column")

    print("Pass 1/3: counting cleaned rows for a chronological train/val row cutoff...")
    total_rows, _per_file_rows = count_cleaned_rows(args.data, feature_cols, label_col, timestamp_col, args.chunksize)
    row_cutoff = int(total_rows * TRAIN_FRACTION)
    print(f"  -> {total_rows} cleaned rows total across {len(args.data)} file(s); "
          f"scaler will see only the first {row_cutoff} (chronological train split)")

    print("Pass 2/3: fitting scaler (streaming, TRAIN ROWS ONLY -- no val/test leakage)...")
    scaler = fit_scaler_streaming(args.data, feature_cols, label_col, timestamp_col, args.chunksize,
                                   row_cutoff=row_cutoff)

    print("Pass 3/3: building network states (streaming)...")
    all_X, all_y = [], []
    for path in args.data:
        chunks = iter_csv_chunks(path, feature_cols, label_col, timestamp_col, args.chunksize)
        states, _ = build_states_for_file(chunks, feature_cols, std_cols, scaler, args.window_size, label_col)
        if len(states) <= args.seq_len:
            print(f"  [skip] {path}: only {len(states)} states, need > seq_len={args.seq_len}")
            continue
        X, y = build_sequences(states, args.seq_len)
        all_X.append(X)
        all_y.append(y)
        print(f"  {path}: {len(states)} states -> {len(X)} sequences")

    if not all_X:
        raise RuntimeError("No usable sequences produced. Check window_size/seq_len vs dataset size.")

    X = np.concatenate(all_X, axis=0)
    y = np.concatenate(all_y, axis=0)
    print(f"Total sequences: {X.shape}, targets: {y.shape}")

    split = int(len(X) * TRAIN_FRACTION)  # sequential split -- preserves time order, no shuffling across the
    # boundary, and uses the SAME fraction as the row-level cutoff the scaler was fit against above, so the
    # sequences that end up in X_val were never seen by the scaler either.
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    train_loader = DataLoader(TensorDataset(torch.tensor(X_train), torch.tensor(y_train)),
                               batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.tensor(X_val), torch.tensor(y_val)),
                             batch_size=args.batch_size, shuffle=False)

    input_size = X.shape[-1]

    # Baseline stats for anomaly/risk scoring are a property of the training
    # data, not of any particular epoch's model, so they're computed once
    # here rather than recomputed on every improved checkpoint.
    #
    # active_mask flags which state dimensions have real variance in the
    # training distribution. A dimension that's structurally constant here
    # (e.g. flow_count, which always equals window_size) is excluded from
    # anomaly scoring entirely rather than epsilon-floored -- see
    # app/forecasting/zscore.py for why. Because this is derived from the
    # *actual* per-dimension std rather than hardcoded to a feature name, it
    # stays correct if window_size changes, features are added/removed, or a
    # different dataset makes some other dimension constant.
    flat_train = X_train.reshape(-1, input_size)
    baseline_mean = flat_train.mean(axis=0)
    baseline_std_raw = flat_train.std(axis=0)
    active_mask = derive_active_mask(baseline_std_raw)
    # Tiny numerical floor only on ACTIVE dims, purely to avoid a literal
    # zero-division edge case -- inactive dims are never divided by their
    # stored std at all, since active_mask routes them to /inf instead.
    baseline_std = np.where(active_mask, np.maximum(baseline_std_raw, 1e-6), baseline_std_raw)

    excluded_names = [name for name, active in
                       zip(get_state_feature_names(feature_cols, std_cols), active_mask) if not active]
    if excluded_names:
        print(f"Excluded {len(excluded_names)} near-constant dim(s) from anomaly scoring "
              f"(std <= threshold, e.g. structurally constant at this window_size): {excluded_names}")

    model = GRUWorldModel(input_size, args.hidden_size, args.num_layers).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = torch.nn.MSELoss()

    best_val = float("inf")
    patience_ctr = 0
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            optim.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses = []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_losses.append(loss_fn(model(xb), yb).item())

        train_mean = float(np.mean(train_losses))
        val_mean = float(np.mean(val_losses)) if val_losses else float("nan")
        print(f"Epoch {epoch}/{epochs} - train_loss={train_mean:.5f} val_loss={val_mean:.5f}")

        if val_mean < best_val:
            best_val = val_mean
            patience_ctr = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "input_size": input_size,
                "hidden_size": args.hidden_size,
                "num_layers": args.num_layers,
                "seq_len": args.seq_len,
                "window_size": args.window_size,
                "selected_features": feature_cols,
                "state_std_features": std_cols,
                "state_feature_names": get_state_feature_names(feature_cols, std_cols),
                "baseline_mean": baseline_mean.tolist(),
                "baseline_std": baseline_std.tolist(),
                "anomaly_active_mask": active_mask.tolist(),
                "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "mode": args.mode,
                "best_val_loss": best_val,
            }, os.path.join(args.checkpoint_dir, "world_model.pt"))
            joblib.dump(scaler, os.path.join(args.checkpoint_dir, "scaler.pkl"))
            print(f"  -> checkpoint saved (val_loss improved to {best_val:.5f})")
        else:
            patience_ctr += 1
            if patience_ctr >= args.patience:
                print(f"Early stopping at epoch {epoch}")
                break

    print("Training complete. Best val loss:", best_val)


if __name__ == "__main__":
    main()
