import numpy as np
import torch


def explain_risk(model, risk_fn, state_history, state_feature_names,
                  baseline_mean, baseline_std, top_k=5, perturb_sigma=1.0):
    device = next(model.parameters()).device
    history = np.array(state_history, dtype="float32")

    model.eval()
    with torch.no_grad():
        base_pred = model(torch.tensor(history[None], device=device)).cpu().numpy()[0]
    base_risk = risk_fn(base_pred)

    results = []
    for i, name in enumerate(state_feature_names):
        perturbed = history.copy()
        original_value = float(perturbed[-1, i])
        perturbed_value = original_value + perturb_sigma
        perturbed[-1, i] = perturbed_value

        with torch.no_grad():
            pred = model(torch.tensor(perturbed[None], device=device)).cpu().numpy()[0]
        risk = risk_fn(pred)

        results.append({
            "feature": name,
            "original_value": original_value,
            "perturbed_value": perturbed_value,
            "risk_delta": float(risk - base_risk),
        })

    results.sort(key=lambda r: abs(r["risk_delta"]), reverse=True)
    return base_risk, results[:top_k]
