from fastapi import APIRouter, HTTPException
import numpy as np

from app.core.model_registry import registry
from app.core.schemas import (
    ForecastRequest, ForecastResponse, RolloutRequest, RolloutResponse,
    ExplainRequest, ExplainResponse, ModelStatusResponse,
)
from app.forecasting.rollout import rollout
from app.forecasting.risk_engine import compute_risk_score, risk_over_rollout
from app.forecasting.stage_mapper import build_feature_groups, predict_stage
from app.explainability.perturbation import explain_risk

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/model/status/internal", response_model=ModelStatusResponse)
def model_status_internal():
    """Low-level checkpoint status for the core ML API (hidden_size etc.).
    The dashboard's richer /api/model/status lives in app/api/dashboard_routes.py."""
    if not registry.loaded:
        return ModelStatusResponse(loaded=False)
    cfg = registry.config
    return ModelStatusResponse(
        loaded=True, input_size=cfg["input_size"], hidden_size=cfg["hidden_size"],
        seq_len=cfg["seq_len"], trained_at=cfg.get("trained_at"), mode=cfg.get("mode"),
    )


def _check_loaded():
    if not registry.loaded:
        raise HTTPException(503, "Model not trained/loaded yet. Run train.py first.")


def _validate_history(state_history):
    cfg = registry.config
    if len(state_history) != cfg["seq_len"]:
        raise HTTPException(400, f"state_history must have exactly {cfg['seq_len']} states")
    for s in state_history:
        if len(s) != cfg["input_size"]:
            raise HTTPException(400, f"each state must have {cfg['input_size']} features")


@router.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    _check_loaded()
    _validate_history(req.state_history)
    cfg = registry.config
    baseline_mean = np.array(cfg["baseline_mean"])
    baseline_std = np.array(cfg["baseline_std"])
    active_mask = np.array(cfg["anomaly_active_mask"]) if "anomaly_active_mask" in cfg else None

    preds, _diagnostics = rollout(registry.model, req.state_history, req.K)
    forecast_risk, _, _peak_risk = risk_over_rollout(preds, baseline_mean, baseline_std, active_mask)

    groups = build_feature_groups(cfg["selected_features"])
    stage, _ = predict_stage(preds[-1], baseline_mean, baseline_std, groups, active_mask)

    _, top_features = explain_risk(
        registry.model, lambda s: compute_risk_score(s, baseline_mean, baseline_std, active_mask),
        req.state_history, cfg["state_feature_names"], baseline_mean, baseline_std, top_k=5,
    )

    return ForecastResponse(
        risk_score=forecast_risk,
        forecast_horizon=req.K,
        predicted_stage=stage,
        driving_features=top_features,
        predicted_states=[p.tolist() for p in preds],
    )


@router.post("/rollout", response_model=RolloutResponse)
def rollout_endpoint(req: RolloutRequest):
    _check_loaded()
    _validate_history(req.state_history)
    cfg = registry.config
    baseline_mean = np.array(cfg["baseline_mean"])
    baseline_std = np.array(cfg["baseline_std"])
    active_mask = np.array(cfg["anomaly_active_mask"]) if "anomaly_active_mask" in cfg else None
    preds, _diagnostics = rollout(registry.model, req.state_history, req.K)
    _, per_step, _ = risk_over_rollout(preds, baseline_mean, baseline_std, active_mask)
    return RolloutResponse(predicted_states=[p.tolist() for p in preds], per_step_risk=per_step)


@router.post("/explain", response_model=ExplainResponse)
def explain_endpoint(req: ExplainRequest):
    _check_loaded()
    _validate_history(req.state_history)
    cfg = registry.config
    baseline_mean = np.array(cfg["baseline_mean"])
    baseline_std = np.array(cfg["baseline_std"])
    active_mask = np.array(cfg["anomaly_active_mask"]) if "anomaly_active_mask" in cfg else None
    base_risk, top_features = explain_risk(
        registry.model, lambda s: compute_risk_score(s, baseline_mean, baseline_std, active_mask),
        req.state_history, cfg["state_feature_names"], baseline_mean, baseline_std, top_k=req.top_k,
    )
    return ExplainResponse(base_risk=base_risk, driving_features=top_features)
