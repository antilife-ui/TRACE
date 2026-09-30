"""Shared, robust z-score utilities used by risk scoring and stage mapping.

A naive `(x - mean) / (std + eps)` has two structural failure modes:

1. Near-constant / structurally-constant features. `flow_count` is the
   concrete example in this pipeline -- it is always exactly `window_size`,
   so its true std is ~0. Any fixed epsilon floor still turns tiny float
   noise (a rollout prediction landing at 99.98 instead of 100) into a
   z-score in the thousands, which alone can saturate the risk score. The
   fix is not a bigger epsilon (that just moves the same failure to a new
   threshold, and reappears for whichever feature is next to become
   constant -- e.g. after changing window_size from 100 to 200). The fix is
   to recognize "this dimension never varies" as a data property and
   exclude it from anomaly scoring entirely.
2. Non-finite inputs. A degenerate baseline_std passed in without a mask,
   or a model producing a non-finite prediction during rollout, should not
   be allowed to silently dominate or blow up the score. Concretely: a
   NaN/Inf entry in `state_vector` is substituted with the baseline mean
   for that dimension (z = 0, i.e. "no signal available"), never clipped
   to +/-z_clip ("maximum anomaly") the way it was previously. The caller
   gets an explicit `input_finite` flag so it can surface a stability
   diagnostic instead of quietly presenting a numerical failure as a
   genuine attack signal.

Both risk_engine.compute_risk_score and stage_mapper.predict_stage score
z-scores against the same baseline, so the logic lives here once.
"""
import numpy as np

# A baseline std below this is treated as "no real variance" -- the
# dimension is structurally constant (or close enough) in the training
# distribution, so it's excluded from anomaly scoring rather than
# epsilon-floored. This is a property of the data (did this feature ever
# move across the training set?), not of any specific feature name or
# window size, so it stays correct if window_size, the feature set, or the
# dataset changes later.
NEAR_CONSTANT_STD_THRESHOLD = 1e-3

# A single dimension's z-score is capped at this magnitude before it's
# averaged into the anomaly score, so one outlier or degenerate dimension
# can't single-handedly saturate the risk score the way flow_count's
# ~1e-6 std currently does.
DEFAULT_Z_CLIP = 6.0


def derive_active_mask(baseline_std, threshold=NEAR_CONSTANT_STD_THRESHOLD):
    """Boolean mask of dimensions with enough real variance to be scored.

    Used both to build the mask at training time (from the *raw*,
    unfloored std) and as a fallback at call time for any baseline_std
    that wasn't shipped with an explicit mask.
    """
    baseline_std = np.asarray(baseline_std, dtype="float64")
    return baseline_std > threshold


def safe_zscore(state_vector, baseline_mean, baseline_std, active_mask=None,
                 z_clip=DEFAULT_Z_CLIP):
    """Per-dimension z-score, robust to constant features and non-finite input.

    Inactive dimensions (per active_mask) are always exactly 0 -- they
    divide by infinity rather than by a floored-near-zero std, so they
    can never contribute noise.

    Any dimension where the INPUT state_vector itself is NaN/Inf is
    substituted with the baseline mean before scoring, so it contributes
    z=0 ("no anomaly signal available") rather than being clipped to
    +/-z_clip ("maximum anomaly") -- a non-finite reading is a numerical
    failure, not evidence of an attack, and must not be scored as one.

    The remaining nan_to_num/clip below is a backstop for a degenerate
    baseline_std (e.g. zero passed in without a mask), not for bad model
    output -- that's handled by the substitution above. Every dimension is
    still clamped to +/-z_clip afterwards.

    Returns (z, active_mask_used, input_finite) where input_finite is
    False iff state_vector contained any NaN/Inf.
    """
    state_vector = np.asarray(state_vector, dtype="float64")
    baseline_mean = np.asarray(baseline_mean, dtype="float64")
    baseline_std = np.asarray(baseline_std, dtype="float64")

    if active_mask is None:
        active_mask = derive_active_mask(baseline_std)
    active_mask = np.asarray(active_mask, dtype=bool)

    finite_input = np.isfinite(state_vector)
    input_finite = bool(np.all(finite_input))
    # Non-finite entries stand in as "at baseline" (z=0) rather than being
    # left to blow up the division below.
    safe_state = np.where(finite_input, state_vector, baseline_mean)

    safe_std = np.where(active_mask, baseline_std, np.inf)
    z = (safe_state - baseline_mean) / safe_std

    # Backstop only: a degenerate baseline_std/mean combination could still
    # produce non-finite z here even with finite input.
    z = np.nan_to_num(z, nan=0.0, posinf=z_clip, neginf=-z_clip)
    z = np.clip(z, -z_clip, z_clip)
    return z, active_mask, input_finite
