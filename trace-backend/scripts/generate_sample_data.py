import argparse
import os
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "Flow Duration", "Total Fwd Packets", "Total Backward Packets",
    "Total Length of Fwd Packets", "Total Length of Bwd Packets",
    "Fwd Packet Length Mean", "Fwd Packet Length Std",
    "Bwd Packet Length Mean", "Bwd Packet Length Std",
    "Flow Bytes/s", "Flow Packets/s",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Mean", "Fwd IAT Std", "Bwd IAT Mean", "Bwd IAT Std",
    "Fwd PSH Flags", "SYN Flag Count", "RST Flag Count",
    "PSH Flag Count", "ACK Flag Count", "Down/Up Ratio",
    "Average Packet Size", "Init_Win_bytes_forward", "Init_Win_bytes_backward",
    "Active Mean", "Idle Mean",
]

ATTACK_PROFILES = {
    "DoS Hulk": dict(scale={"Total Fwd Packets": 8, "Flow Bytes/s": 6, "Flow Packets/s": 6}, iat_shrink=0.1),
    "DDoS": dict(scale={"Total Fwd Packets": 10, "Total Backward Packets": 8, "Flow Bytes/s": 8}, iat_shrink=0.05),
    "PortScan": dict(scale={"SYN Flag Count": 6, "RST Flag Count": 4}, iat_shrink=0.3, packet_shrink=0.2),
    "Bot": dict(scale={"Flow IAT Std": 3, "Active Mean": 2}, iat_shrink=0.6),
}


def base_row(rng):
    row = {
        "Flow Duration": rng.exponential(500_000),
        "Total Fwd Packets": rng.poisson(10) + 1,
        "Total Backward Packets": rng.poisson(8) + 1,
        "Fwd Packet Length Mean": rng.normal(300, 60),
        "Fwd Packet Length Std": abs(rng.normal(50, 15)),
        "Bwd Packet Length Mean": rng.normal(300, 60),
        "Bwd Packet Length Std": abs(rng.normal(50, 15)),
        "Flow Bytes/s": rng.exponential(2000),
        "Flow Packets/s": rng.exponential(20),
        "Flow IAT Mean": rng.exponential(50_000),
        "Flow IAT Std": abs(rng.normal(20_000, 5000)),
        "Fwd IAT Mean": rng.exponential(40_000),
        "Fwd IAT Std": abs(rng.normal(15_000, 4000)),
        "Bwd IAT Mean": rng.exponential(40_000),
        "Bwd IAT Std": abs(rng.normal(15_000, 4000)),
        "Fwd PSH Flags": rng.poisson(1),
        "SYN Flag Count": rng.poisson(1),
        "RST Flag Count": rng.poisson(0.5),
        "PSH Flag Count": rng.poisson(1),
        "ACK Flag Count": rng.poisson(5),
        "Down/Up Ratio": rng.uniform(0.2, 2.0),
        "Average Packet Size": rng.normal(300, 60),
        "Init_Win_bytes_forward": rng.choice([-1, 8192, 16384, 65535]),
        "Init_Win_bytes_backward": rng.choice([-1, 8192, 16384, 65535]),
        "Active Mean": rng.exponential(10_000),
        "Idle Mean": rng.exponential(100_000),
    }
    row["Total Length of Fwd Packets"] = row["Total Fwd Packets"] * rng.normal(300, 50)
    row["Total Length of Bwd Packets"] = row["Total Backward Packets"] * rng.normal(300, 50)
    row["Flow IAT Max"] = row["Flow IAT Mean"] * rng.uniform(2, 5)
    row["Flow IAT Min"] = row["Flow IAT Mean"] * rng.uniform(0.01, 0.3)
    return row


def apply_profile(row, profile, rng):
    for feat, factor in profile.get("scale", {}).items():
        row[feat] = row[feat] * factor * rng.uniform(0.8, 1.2)
    if profile.get("iat_shrink"):
        for c in ["Flow IAT Mean", "Flow IAT Std", "Fwd IAT Mean", "Bwd IAT Mean"]:
            row[c] *= profile["iat_shrink"]
    if profile.get("packet_shrink"):
        row["Fwd Packet Length Mean"] *= profile["packet_shrink"]
        row["Bwd Packet Length Mean"] *= profile["packet_shrink"]
    return row


def generate(n_rows, attack_fraction, block_size, seed, out_path):
    rng = np.random.default_rng(seed)
    rows, labels = [], []
    attack_names = list(ATTACK_PROFILES.keys())
    i = 0
    while i < n_rows:
        this_block = min(block_size, n_rows - i)
        if rng.random() < attack_fraction:
            name = rng.choice(attack_names)
            profile = ATTACK_PROFILES[name]
            for _ in range(this_block):
                rows.append(apply_profile(base_row(rng), profile, rng))
                labels.append(name)
        else:
            for _ in range(this_block):
                rows.append(base_row(rng))
                labels.append("BENIGN")
        i += this_block

    df = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    df["Label"] = labels
    df["Timestamp"] = pd.date_range("2017-07-01", periods=len(df), freq="s")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Synthetic sample written to {out_path}: {len(df)} rows, "
          f"{sum(l != 'BENIGN' for l in labels)} attack rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_rows", type=int, default=20000)
    ap.add_argument("--attack_fraction", type=float, default=0.2)
    ap.add_argument("--block_size", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/sample_cicids2017.csv")
    args = ap.parse_args()
    generate(args.n_rows, args.attack_fraction, args.block_size, args.seed, args.out)
