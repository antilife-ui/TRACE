import argparse
import numpy as np
import pandas as pd
from collections import Counter


def inspect(path, chunksize=200_000, label_col_guess="Label"):
    total_rows = 0
    na_counts = inf_counts = None
    columns, dtypes = None, None
    label_counts = Counter()

    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        chunk.columns = [c.strip() for c in chunk.columns]
        if columns is None:
            columns = list(chunk.columns)
            dtypes = chunk.dtypes.to_dict()
            na_counts = pd.Series(0, index=columns)
            inf_counts = pd.Series(0, index=columns)

        total_rows += len(chunk)
        na_counts += chunk.isna().sum()
        numeric_cols = chunk.select_dtypes(include=[np.number]).columns
        inf_counts[numeric_cols] += chunk[numeric_cols].isin([np.inf, -np.inf]).sum()

        label_col = label_col_guess if label_col_guess in chunk.columns else None
        if label_col:
            label_counts.update(chunk[label_col].astype(str).value_counts().to_dict())

    print(f"Total rows: {total_rows}")
    print(f"Columns ({len(columns)}): {columns}")
    print("Dtypes sample:", dtypes)
    print("\nTop missing-value columns:")
    print(na_counts.sort_values(ascending=False).head(15))
    print("\nTop inf-value columns:")
    print(inf_counts.sort_values(ascending=False).head(15))
    print("\nLabel distribution:")
    for k, v in label_counts.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--chunksize", type=int, default=200_000)
    ap.add_argument("--label_col", default="Label")
    args = ap.parse_args()
    inspect(args.path, args.chunksize, args.label_col)
