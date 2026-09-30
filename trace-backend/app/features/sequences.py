import numpy as np


def build_sequences(states, seq_len):
    if len(states) <= seq_len:
        dim = states[0].shape[0] if states else 0
        return np.empty((0, seq_len, dim), dtype="float32"), np.empty((0, dim), dtype="float32")

    arr = np.stack(states)
    X, y = [], []
    for i in range(len(arr) - seq_len):
        X.append(arr[i:i + seq_len])
        y.append(arr[i + seq_len])
    return np.stack(X).astype("float32"), np.stack(y).astype("float32")
