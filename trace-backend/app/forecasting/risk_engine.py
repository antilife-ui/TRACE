import numpy as np

from app.forecasting.zscore import safe_zscore, DEFAULT_Z_CLIP


def compute_risk_score(state_vector, baseline_mean, baseline_std, active_mask=None,
                        alpha=0.5, z_clip=DEFAULT_Z_CLIP, return_diagnostics=False):
    """
    Heuristic anomaly-based risk_score in [0, 1].
    NOT a calibrated probability -- no calibration step has been implemented.

    active_mask (optional): boolean array marking which state dimensions
    carry real anomaly signal. Dimensions with ~zero baseline variance
    (structurally constant features -- e.g. flow_count, which is always
    exactly window_size) are excluded rather than epsilon-floored, and
    every remaining z-score is clipped so no single dimension can saturate
    the score on its own. If omitted, the mask is derived from
    baseline_std at call time (see app.forecasting.zscore), so this is
    safe against constant/near-constant features even when the caller
    doesn't have an explicit mask on hand.

    return_diagnostics: if True, returns (risk, input_finite) instead of
    just risk, where input_finite is False iff state_vector contained
    NaN/Inf (see app.forecasting.zscore.safe_zscore). Defaults to False so
    every existing float-only caller is unaffected.
    """
    z, active_mask, input_finite = safe_zscore(state_vector, baseline_mean, baseline_std,
                                                 active_mask, z_clip)
    n_active = int(np.count_nonzero(active_mask))
    if n_active == 0:
        risk = 0.0
    else:
        # Average over the ACTIVE dimensions only -- excluded dimensions are
        # zero but must not dilute the anomaly score just because there are
        # more of them (e.g. after adding more near-constant features later).
        anomaly = float(np.sum(np.abs(z)) / n_active)
        risk = float(np.clip(1.0 - np.exp(-alpha * anomaly), 0.0, 1.0))
    if return_diagnostics:
        return risk, input_finite
    return risk


def risk_over_rollout(predicted_states, baseline_mean, baseline_std, active_mask=None,
                       alpha=0.5, z_clip=DEFAULT_Z_CLIP, horizon_decay=0.85):
    """
    Score every step of a forecast horizon and reduce it two ways:

      - peak_risk: the worst single step. Still reported -- a sharp spike
        several steps out is real signal and shouldn't be hidden.
      - forecast_risk: a horizon-weighted average, weighted toward the
        near steps (weight = horizon_decay ** step_index). Rollout
        predictions compound error the further out they go, so near-term
        steps are more trustworthy and should dominate the headline
        number; one noisy distant step should not alone be able to drive
        the forecast to ~peak the way a bare max() over the horizon can.

    Returns (forecast_risk, per_step_scores, peak_risk).
    """
    scores = [compute_risk_score(s, baseline_mean, baseline_std, active_mask, alpha, z_clip)
              for s in predicted_states]
    if not scores:
        return 0.0, [], 0.0
    scores_arr = np.asarray(scores)
    peak_risk = float(np.max(scores_arr))
    weights = horizon_decay ** np.arange(len(scores))
    forecast_risk = float(np.sum(weights * scores_arr) / np.sum(weights))
    return forecast_risk, scores, peak_risk
