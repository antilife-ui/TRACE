import numpy as np
import torch

# A predicted state vector with this Euclidean norm or higher is treated as
# "exploded" -- technically finite but far outside anything a real network
# state could plausibly be, which recursive K-step prediction can produce
# once error starts compounding. This is a numerical-stability guard, not a
# cybersecurity threshold: it exists purely to catch runaway model output
# before it's fed back into its own history, and is set high enough that it
# should never fire on a normal (scaler-standardized, roughly unit-scale)
# state vector.
DEFAULT_MAX_STATE_NORM = 1e4


def rollout(model, history_states, K, device=None, max_norm=DEFAULT_MAX_STATE_NORM):
    """K-step recursive rollout with per-step stability diagnostics.

    Each step feeds the model's own prediction back in as the next input,
    so a single bad prediction compounds: if it were fed back in
    unchecked, a NaN/Inf or exploding value at step i would silently
    corrupt every later step, and (before this fix) would then be scored
    by the risk engine as if it were a genuine extreme anomaly. To fail
    safely instead:

      - every predicted vector is validated for the expected dimensionality
        and for finiteness (no NaN/Inf) before being fed back into history
      - its norm is checked against `max_norm` to catch "exploded" values
        that are technically finite but not physically plausible
      - once a step is flagged unstable, the rollout stops feeding that
        corrupted/exploding vector back into the model and instead holds
        the last known-good state steady for the rest of the horizon, so
        callers still get exactly K predictions (nothing downstream has to
        handle a short list), and the per-step diagnostics say plainly
        which steps are real model output vs. held steady after a failure

    Returns (predictions, diagnostics):
      predictions: list of length K of np.ndarray. Steps at/after the
        first instability are the last known-good state repeated, not a
        fabricated continuation of the model's trajectory.
      diagnostics: {
        "stable": bool,               # True iff every step was finite & in-range
        "firstUnstableStep": int|None,  # 1-indexed, None if always stable
        "steps": [{"step": i, "finite": bool, "norm": float|None, "exploded": bool}, ...]
      }
    """
    device = device or next(model.parameters()).device
    history = np.array(history_states, dtype="float32").copy()
    expected_dim = history.shape[-1]

    predictions = []
    step_diags = []
    stable = True
    first_unstable = None
    last_good = history[-1].copy()

    model.eval()
    for step in range(K):
        with torch.no_grad():
            x = torch.tensor(history[None], dtype=torch.float32, device=device)
            pred = model(x).cpu().numpy()[0]

        right_shape = pred.shape[-1] == expected_dim
        finite = right_shape and bool(np.all(np.isfinite(pred)))
        norm = float(np.linalg.norm(pred)) if finite else None
        exploded = finite and norm > max_norm

        if not finite or exploded:
            stable = False
            if first_unstable is None:
                first_unstable = step + 1
            # Do not feed the corrupted/exploding vector back into the
            # model, and do not let the risk engine score it either --
            # hold the last known-good state steady so the degraded region
            # of the forecast is flat and clearly flagged instead of
            # presenting a numerical failure as a spike in risk.
            safe_pred = last_good.copy()
        else:
            safe_pred = pred
            last_good = pred.copy()

        predictions.append(safe_pred)
        step_diags.append({
            "step": step + 1,
            "finite": finite,
            "norm": round(norm, 3) if norm is not None else None,
            "exploded": exploded,
        })
        history = np.vstack([history[1:], safe_pred[None, :]])

    diagnostics = {"stable": stable, "firstUnstableStep": first_unstable, "steps": step_diags}
    return predictions, diagnostics
