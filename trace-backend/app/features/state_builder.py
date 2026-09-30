import numpy as np


def get_state_feature_names(feature_cols, std_cols):
    return list(feature_cols) + [f"{c}_std" for c in std_cols] + ["flow_count"]


def build_states_for_file(chunks_iterable, feature_cols, std_feature_cols, scaler, window_size, label_col=None):
    std_idx = [feature_cols.index(c) for c in std_feature_cols]

    buffer_X, buffer_labels = [], []
    states, metas = [], []

    for chunk in chunks_iterable:
        X = scaler.transform(chunk[feature_cols].values).astype("float32")
        labels = chunk[label_col].values if (label_col and label_col in chunk.columns) else None

        for i in range(len(chunk)):
            buffer_X.append(X[i])
            if labels is not None:
                buffer_labels.append(labels[i])

            if len(buffer_X) == window_size:
                arr = np.array(buffer_X, dtype="float32")
                mean_vec = arr.mean(axis=0)
                std_vec = arr[:, std_idx].std(axis=0)
                flow_count = np.array([window_size], dtype="float32")
                state_vec = np.concatenate([mean_vec, std_vec, flow_count])
                states.append(state_vec)

                if buffer_labels:
                    vals, counts = np.unique(buffer_labels, return_counts=True)
                    dominant = str(vals[np.argmax(counts)])
                    attack_fraction = float(np.mean([str(l) != "BENIGN" for l in buffer_labels]))
                else:
                    dominant, attack_fraction = None, None

                metas.append({"dominant_label": dominant, "attack_fraction": attack_fraction})
                buffer_X, buffer_labels = [], []

    return states, metas
