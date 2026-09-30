"""Validate the real TRACE dataset before training.
Usage: python scripts/prepare_real_dataset.py --path data/CIC_IDS2017_PS1_Cleaned.csv
"""
import argparse, json
import pandas as pd

ap=argparse.ArgumentParser(); ap.add_argument("--path", required=True); ap.add_argument("--config", default="configs/feature_config.json"); args=ap.parse_args()
with open(args.config) as f: cfg=json.load(f)
features=cfg["selected_features"]; df=pd.read_csv(args.path, nrows=1000, low_memory=False); df.columns=[c.strip() for c in df.columns]
missing=[c for c in features if c not in df.columns]
print(f"Columns found: {len(df.columns)}")
print(f"Required features: {len(features)}")
print("Missing required features:", missing if missing else "none")
print("Timestamp configured:", cfg.get("timestamp_column"))
print("Label column present:", cfg.get("label_column") in df.columns)
if missing: raise SystemExit(1)
print("Dataset schema is compatible with TRACE.")
