"""Quick smoke test on a tiny synthetic dataset. Run: python tests/test_pipeline.py"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import torch

from scripts.generate_sample_data import generate
from app.features.preprocessing import fit_scaler_streaming
from app.data.loader import iter_csv_chunks
from app.features.state_builder import build_states_for_file, get_state_feature_names
from app.features.sequences import build_sequences
from app.models.gru_world_model import GRUWorldModel
from app.forecasting.rollout import rollout
from app.forecasting.risk_engine import compute_risk_score, risk_over_rollout
from app.forecasting.stage_mapper import build_feature_groups, predict_stage
from app.explainability.perturbation import explain_risk

TMP_CSV = "data/_test_sample.csv"
CONFIG_PATH = "configs/feature_config.json"


def run():
    print("1) generating tiny synthetic dataset...")
    generate(n_rows=600, attack_fraction=0.3, block_size=50, seed=1, out_path=TMP_CSV)

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    feature_cols, std_cols = cfg["selected_features"], cfg["state_std_features"]
    label_col, timestamp_col = cfg["label_column"], cfg["timestamp_column"]
    window_size, seq_len = 10, 5

    print("2) fitting scaler...")
    scaler = fit_scaler_streaming([TMP_CSV], feature_cols, label_col, timestamp_col, chunksize=1000)

    print("3) building states...")
    chunks = iter_csv_chunks(TMP_CSV, feature_cols, label_col, timestamp_col, chunksize=1000)
    states, metas = build_states_for_file(chunks, feature_cols, std_cols, scaler, window_size, label_col)
    assert len(states) > seq_len
    print(f"   -> {len(states)} states")

    print("4) building sequences...")
    X, y = build_sequences(states, seq_len)
    input_size = X.shape[-1]
    print(f"   -> X {X.shape}, y {y.shape}")

    print("5) GRU forward pass...")
    model = GRUWorldModel(input_size, hidden_size=32, num_layers=1)
    with torch.no_grad():
        out = model(torch.tensor(X[:4]))
    assert out.shape == (4, input_size)

    print("6) one training step...")
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()
    xb, yb = torch.tensor(X), torch.tensor(y)
    for _ in range(3):
        opt.zero_grad()
        loss = loss_fn(model(xb), yb)
        loss.backward()
        opt.step()
    print(f"   -> loss: {loss.item():.5f}")

    print("7) checkpoint save/load...")
    os.makedirs("checkpoints", exist_ok=True)
    baseline_mean = X.reshape(-1, input_size).mean(axis=0)
    baseline_std = X.reshape(-1, input_size).std(axis=0) + 1e-6
    state_feature_names = get_state_feature_names(feature_cols, std_cols)
    ckpt = {
        "model_state_dict": model.state_dict(), "input_size": input_size,
        "hidden_size": 32, "num_layers": 1, "seq_len": seq_len, "window_size": window_size,
    }
    torch.save(ckpt, "checkpoints/_test_model.pt")
    loaded = torch.load("checkpoints/_test_model.pt", map_location="cpu")
    model2 = GRUWorldModel(loaded["input_size"], loaded["hidden_size"], loaded["num_layers"])
    model2.load_state_dict(loaded["model_state_dict"])
    model2.eval()

    print("8) rollout...")
    preds, diagnostics = rollout(model2, X[0], K=3)
    assert len(preds) == 3
    assert diagnostics["stable"] is True

    print("9) risk score...")
    forecast_risk, per_step, peak_risk = risk_over_rollout(preds, baseline_mean, baseline_std)
    assert 0.0 <= forecast_risk <= 1.0
    assert 0.0 <= peak_risk <= 1.0
    assert len(per_step) == len(preds)

    print("10) stage mapping...")
    groups = build_feature_groups(feature_cols)
    stage, _ = predict_stage(preds[-1], baseline_mean, baseline_std, groups)
    print(f"   -> stage: {stage}")

    print("11) explanation...")
    base_risk, top_feats = explain_risk(
        model2, lambda s: compute_risk_score(s, baseline_mean, baseline_std),
        X[0], state_feature_names, baseline_mean, baseline_std, top_k=3,
    )
    assert len(top_feats) == 3
    print(f"   -> base_risk={base_risk:.4f}, top feature: {top_feats[0]['feature']}")

    print("12) flow_count regression test (near-zero-variance dimension)...")
    # Reproduces the original bug directly: a baseline where one dimension
    # (flow_count-like) has near-zero std because it's structurally constant
    # in training (e.g. always == window_size), while other dimensions carry
    # real variance. Before the fix, a tiny float deviation in that one
    # dimension alone (e.g. 100 -> 100.001) could saturate risk to ~1.0 via
    # a huge z-score; after the fix it must not, for any flow_count value.
    from app.forecasting.zscore import derive_active_mask
    reg_baseline_mean = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 100.0])  # last dim: flow_count, baseline = window_size
    reg_baseline_std = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1e-6])    # flow_count std ~= 1e-6, like the original bug
    reg_active_mask = derive_active_mask(reg_baseline_std)
    assert not reg_active_mask[-1], "flow_count dim must be excluded (near-zero baseline std)"
    assert reg_active_mask[:-1].all(), "the other, genuinely-variable dims must remain active"

    for flow_count_value in (90.0, 100.0, 100.001, 110.0):
        state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, flow_count_value])  # every other dim exactly at baseline
        risk = compute_risk_score(state, reg_baseline_mean, reg_baseline_std, reg_active_mask)
        assert np.isfinite(risk), f"risk not finite for flow_count={flow_count_value}"
        assert risk < 0.05, (
            f"flow_count={flow_count_value} alone must not dominate risk (got {risk:.4f}) -- "
            "this is exactly the original near-zero-variance saturation bug"
        )
    print("   -> flow_count deviations (90, 100, 100.001, 110) never dominate risk; all finite")

    # Same check with NO explicit mask -- compute_risk_score must derive one
    # itself from baseline_std (the call-time fallback in zscore.py), so
    # callers that don't have a mask handy are equally protected.
    risk_no_mask = compute_risk_score(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 100.001]),
                                       reg_baseline_mean, reg_baseline_std)
    assert risk_no_mask < 0.05
    print(f"   -> derived-mask fallback also safe: risk={risk_no_mask:.4f}")

    print("13) active-mask behavior on real trained states...")
    flat_all = X.reshape(-1, input_size)
    full_std = flat_all.std(axis=0)
    trained_active_mask = derive_active_mask(full_std)
    flow_count_idx = state_feature_names.index("flow_count")
    assert not trained_active_mask[flow_count_idx], "flow_count must be excluded from anomaly scoring"
    n_active = int(trained_active_mask.sum())
    # window_size is fixed in this test, so flow_count is exactly constant and
    # must be excluded; allow a little slack for any other near-constant
    # dimension the tiny synthetic dataset happens to produce, rather than
    # asserting an exact count that could make this test flaky.
    assert n_active >= input_size - 3, f"unexpectedly few active dims: {n_active}/{input_size}"
    print(f"   -> active dims: {n_active}/{input_size} (flow_count excluded, as expected)")

    risk_masked = compute_risk_score(X[0][-1], baseline_mean, baseline_std, trained_active_mask)
    assert np.isfinite(risk_masked)
    print(f"   -> risk with derived training-time mask is finite: {risk_masked:.4f}")

    print("14) forecast_risk is a weighted aggregation, not just the peak...")
    # Three synthetic predicted states: mildly anomalous, back to normal, then
    # sharply anomalous. peak_risk must catch the distant spike; forecast_risk
    # (weighted toward near steps) must dampen it relative to the calmer
    # nearer steps, so the two should differ.
    mild = baseline_mean.copy()
    mild[0] += 2 * baseline_std[0]
    normal = baseline_mean.copy()
    sharp = baseline_mean.copy()
    sharp[0] += 10 * baseline_std[0]

    forecast_risk_2, per_step_2, peak_risk_2 = risk_over_rollout([mild, normal, sharp], baseline_mean, baseline_std)
    assert np.isfinite(forecast_risk_2) and np.isfinite(peak_risk_2)
    assert peak_risk_2 == max(per_step_2)
    assert forecast_risk_2 < peak_risk_2, (
        "forecast_risk must be a horizon-weighted average, not simply the peak -- "
        "a distant spike should be dampened relative to nearer, calmer steps"
    )
    print(f"   -> forecast_risk={forecast_risk_2:.4f} < peak_risk={peak_risk_2:.4f} (weighted aggregation confirmed)")

    print("15) rollout stability diagnostics (fail-safe on non-finite model output)...")

    class _NaNAfterOneStep(torch.nn.Module):
        """Test double: returns a finite pass-through on the first call, then
        NaN on every call after -- simulates a model that goes numerically
        unstable partway through a K-step rollout."""

        def __init__(self, dim):
            super().__init__()
            self.dim = dim
            self.calls = 0
            self.dummy = torch.nn.Parameter(torch.zeros(1))

        def forward(self, x):
            self.calls += 1
            if self.calls >= 2:
                return torch.full((x.shape[0], self.dim), float("nan"))
            return x[:, -1, :]

    broken_model = _NaNAfterOneStep(input_size)
    broken_preds, broken_diag = rollout(broken_model, X[0], K=4)
    assert len(broken_preds) == 4, "rollout must always return exactly K predictions, even after a failure"
    assert broken_diag["stable"] is False
    assert broken_diag["firstUnstableStep"] == 2
    assert all(np.all(np.isfinite(p)) for p in broken_preds), "held-steady fallback states must be finite"
    for p in broken_preds[1:]:
        assert np.allclose(p, broken_preds[0]), "steps after a failure must hold the last known-good state steady"
    print(f"   -> firstUnstableStep={broken_diag['firstUnstableStep']}, "
          f"held steady for the remaining {4 - broken_diag['firstUnstableStep'] + 1} step(s); all finite")

    print("\nALL SANITY CHECKS PASSED.")


if __name__ == "__main__":
    run()
