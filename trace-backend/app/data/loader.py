import pandas as pd
import numpy as np


def clean_chunk(df, feature_cols, label_col=None, timestamp_col=None):
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")

    cols_needed = list(feature_cols)
    if label_col and label_col in df.columns:
        cols_needed.append(label_col)
    if timestamp_col and timestamp_col in df.columns:
        cols_needed.append(timestamp_col)

    df = df[cols_needed].copy()

    if label_col and label_col in df.columns:
        df[label_col] = df[label_col].astype("string").str.replace("�", "-", regex=False).str.strip()

    for c in feature_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=feature_cols)
    df[feature_cols] = df[feature_cols].astype("float32")

    return df.reset_index(drop=True)


def iter_csv_chunks(path, feature_cols, label_col=None, timestamp_col=None, chunksize=200_000):
    """Streams a CSV of any size (2.7M+ rows) without loading it fully into memory."""
    reader = pd.read_csv(path, chunksize=chunksize, low_memory=False)
    for chunk in reader:
        cleaned = clean_chunk(chunk, feature_cols, label_col, timestamp_col)
        if len(cleaned) > 0:
            yield cleaned
