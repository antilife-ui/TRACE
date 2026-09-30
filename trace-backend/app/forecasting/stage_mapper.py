import numpy as np

from app.forecasting.zscore import safe_zscore

STAGE_LOOKUP = {
    "volume_duration": "Denial of Service",
    "iat_variability": "Reconnaissance",
    "flags": "Initial Access",
    "bwd_dominance": "Exfiltration",
}


def build_feature_groups(feature_cols):
    def idxs(keywords):
        return [i for i, c in enumerate(feature_cols) if any(k.lower() in c.lower() for k in keywords)]

    return {
        "volume_duration": idxs(["Flow Duration", "Total Fwd Packets", "Total Backward Packets",
                                  "Flow Bytes/s", "Flow Packets/s"]),
        "iat_variability": idxs(["IAT Std", "IAT Mean"]),
        "flags": idxs(["SYN Flag", "RST Flag", "PSH Flag", "ACK Flag"]),
        "bwd_dominance": idxs(["Bwd Packet Length", "Total Length of Bwd Packets"]),
    }


def predict_stage(state_vector, baseline_mean, baseline_std, groups, active_mask=None, threshold=1.0):
    """Prototype-only heuristic mapping -- illustrative, not scientifically validated.

    Uses the same masked, clipped z-score as risk_engine.compute_risk_score,
    so a structurally constant feature (or a non-finite prediction) can't
    blow up a group's score here either.
    """
    z, _, _ = safe_zscore(state_vector, baseline_mean, baseline_std, active_mask)
    z = np.abs(z)
    n_mean_dims = len(baseline_mean)  # groups index into the "mean" portion of the state vector
    scores = {}
    for group, idx_list in groups.items():
        valid = [i for i in idx_list if i < n_mean_dims]
        scores[group] = float(np.mean(z[valid])) if valid else 0.0

    top_group = max(scores, key=scores.get) if scores else None
    if not top_group or scores[top_group] < threshold:
        return "Normal / Benign-like", scores
    return STAGE_LOOKUP[top_group], scores
