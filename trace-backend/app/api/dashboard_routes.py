"""
Endpoints shaped exactly to match the contracts documented in
frontend/src/utils/mockData.js (NetworkState, Forecast, RiskTimeline,
AttackStage, AttackPath, TelemetryFlow, Explanation, Incident, ModelStatus).

Where the underlying dataset can't honestly support part of a contract --
notably host/IP topology for the attack-path graph, and flow identifiers
(source IP/port, protocol) for telemetry rows -- this module says so in a
comment at the point it fills that gap with a clearly-labeled placeholder,
rather than presenting a guess as a measurement. See README.md, "What's
real vs. placeholder in this integration".
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core import config as cfg
from app.core.live_engine import engine
from app.core.model_registry import registry
from app.explainability.perturbation import explain_risk
from app.forecasting.risk_engine import compute_risk_score, risk_over_rollout
from app.forecasting.rollout import rollout
from app.forecasting.stage_mapper import predict_stage

router = APIRouter()


def _require_engine():
    if not engine.ready:
        detail = engine.error or "live engine not ready"
        raise HTTPException(503, f"Dashboard data unavailable: {detail}")


def _iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def _predicted_states(K):
    """Rolls out K steps and scores each one.

    Returns (states, forecast_risk, peak_risk, model_stable):
      - forecast_risk: horizon-weighted risk (see risk_engine.risk_over_rollout),
        computed ONLY over steps the rollout itself reports as numerically
        stable -- a step held steady after a model failure (see
        app.forecasting.rollout) never contributes to the headline number.
      - peak_risk: the worst STABLE step's score.
      - model_stable: False if any step in the horizon was flagged unstable
        by the rollout (NaN/Inf or exploding prediction).
      Each entry in `states` carries its own `modelStable`; an unstable
      step gets riskScore/stage = None rather than a number derived from
      a held-steady placeholder presented as a real prediction.
    """
    history = engine.history()
    preds, diagnostics = rollout(registry.model, history, K)
    stable_flags = [d["finite"] and not d["exploded"] for d in diagnostics["steps"]]
    stable_preds = [p for p, ok in zip(preds, stable_flags) if ok]

    if stable_preds:
        forecast_risk, stable_scores, peak_risk = risk_over_rollout(
            stable_preds, engine.baseline_mean, engine.baseline_std, engine.anomaly_active_mask)
    else:
        forecast_risk, stable_scores, peak_risk = None, [], None

    states = []
    score_iter = iter(stable_scores)
    for step, (vec, ok) in enumerate(zip(preds, stable_flags), start=1):
        if ok:
            risk = next(score_iter)
            stage, _ = predict_stage(vec, engine.baseline_mean, engine.baseline_std, engine.groups,
                                      engine.anomaly_active_mask)
            states.append({
                "step": step,
                "windowId": f"forecast-{step}",
                "riskScore": round(float(risk), 3),
                "stage": stage,
                "modelStable": True,
            })
        else:
            states.append({
                "step": step,
                "windowId": f"forecast-{step}",
                "riskScore": None,
                "stage": None,
                "modelStable": False,
            })
    return states, forecast_risk, peak_risk, diagnostics["stable"]


# --------------------------------------------------------------------- #
# Model status
# --------------------------------------------------------------------- #
@router.get("/model/status")
def model_status():
    if not registry.loaded:
        return {"name": "TRACE World Model", "type": "GRU", "status": "unavailable"}

    ckpt = registry.config
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"

    mem = {"ramUsedMb": None, "ramTotalMb": None, "gpuVramUsedMb": None, "gpuVramTotalMb": None}
    try:
        import psutil
        vm = psutil.virtual_memory()
        mem["ramUsedMb"] = round((vm.total - vm.available) / 1e6)
        mem["ramTotalMb"] = round(vm.total / 1e6)
    except Exception:
        pass  # psutil not installed -- memory fields stay null rather than fabricated
    if device == "cuda":
        try:
            mem["gpuVramUsedMb"] = round(torch.cuda.memory_allocated() / 1e6)
            mem["gpuVramTotalMb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e6)
        except Exception:
            pass

    perf = engine.performance or {}
    status = "ready" if engine.ready else "degraded"

    return {
        "name": "TRACE World Model",
        "type": "GRU",
        "status": status,
        "version": ckpt.get("mode", "unknown"),
        "stateFeatures": ckpt["input_size"],
        "sequenceLength": ckpt["seq_len"],
        "windowDurationSec": cfg.WINDOW_DURATION_SEC,
        "forecastHorizon": 5,
        "device": device,
        "inferenceLatencyMs": perf.get("inferenceLatencyMs"),
        "lastTrained": ckpt.get("trained_at"),
        "trainingCorpus": {
            "name": engine.dataset_name or "unknown",
            "recordCount": engine.total_rows_seen or None,
        },
        "memory": mem,
        "performance": {
            "f1": perf.get("f1"),
            "precision": perf.get("precision"),
            "recall": perf.get("recall"),
            "rocAuc": perf.get("rocAuc"),
            # Index-based (windows-of-flows), converted via a nominal window duration,
            # not measured wall-clock time -- see live_engine._compute_performance.
            "leadTimeSec": perf.get("leadTimeSec"),
            "kStepError": perf.get("kStepError", []),
        },
    }


# --------------------------------------------------------------------- #
# Forecast
# --------------------------------------------------------------------- #
@router.get("/forecast")
def forecast(horizon: int = Query(5, ge=1, le=20)):
    _require_engine()
    states, forecast_risk, peak_risk, model_stable = _predicted_states(horizon)
    return {
        "generatedAt": _iso(datetime.now(timezone.utc)),
        "currentWindowId": engine.window_id(),
        "horizon": horizon,
        # Headline number is the horizon-weighted forecast risk (near steps
        # weighted more heavily), NOT the risk of the single last step --
        # see risk_engine.risk_over_rollout. None only if every step in the
        # horizon was numerically unstable (see modelStable).
        "riskScore": round(forecast_risk, 3) if forecast_risk is not None else None,
        "peakRisk": round(peak_risk, 3) if peak_risk is not None else None,
        "modelStable": model_stable,
        "states": states,
    }


@router.get("/forecast/risk-timeline")
def risk_timeline():
    _require_engine()
    now = datetime.now(timezone.utc)
    n_observed = 12
    start = max(engine.seq_len - 1, engine.cursor - n_observed + 1)

    # NOTE: the dataset has no reliable per-flow timestamps (feature_config.json sets
    # timestamp_column to null), so these timestamps are synthetically paced using
    # WINDOW_DURATION_SEC, not measured -- consistent with the lead-time caveat
    # documented throughout this project.
    observed = []
    for i in range(start, engine.cursor + 1):
        offset = engine.cursor - i
        observed.append({
            "timestamp": _iso(now - timedelta(seconds=offset * cfg.WINDOW_DURATION_SEC)),
            "value": round(float(engine.risk_at(i)), 3),
            "kind": "observed",
        })

    predicted_states, _forecast_risk, _peak_risk, _model_stable = _predicted_states(5)
    predicted = [
        {
            "timestamp": _iso(now + timedelta(seconds=s["step"] * cfg.WINDOW_DURATION_SEC)),
            "value": s["riskScore"],  # None for a step the rollout flagged unstable
            "kind": "predicted",
        }
        for s in predicted_states
    ]
    return observed + predicted


@router.get("/forecast/attack-stages")
def attack_stages():
    """`score` is the same heuristic anomaly risk_score used everywhere else
    in the app (NOT a calibrated probability). `confidence` has been
    removed rather than filled with a fabricated number: it was previously
    just risk restated (observed/current) or risk*0.85 (predicted), neither
    of which is a real calibration of how confident the model is. No
    calibration step exists in this prototype, so there is nothing honest
    to report here -- see confidenceType below and README, "What's real vs.
    placeholder"."""
    _require_engine()
    entries = []

    for idx in (engine.cursor - 9, engine.cursor - 6, engine.cursor - 3):
        idx = max(engine.seq_len - 1, idx)
        risk = engine.risk_at(idx)
        entries.append({
            "name": engine.stage_at(idx),
            "status": "observed",
            "score": round(float(risk), 3),
            "confidence": None,
            "confidenceType": "not_calibrated",
            "windowId": engine.window_id(idx),
        })

    current_risk = engine.risk_at(engine.cursor)
    entries.append({
        "name": engine.stage_at(engine.cursor),
        "status": "current",
        "score": round(float(current_risk), 3),
        "confidence": None,
        "confidenceType": "not_calibrated",
        "windowId": engine.window_id(),
    })

    predicted_states, _forecast_risk, _peak_risk, _model_stable = _predicted_states(3)
    for s in predicted_states:
        entries.append({
            "name": s["stage"],
            "status": "predicted",
            "score": s["riskScore"],
            "confidence": None,
            "confidenceType": "not_calibrated",
            "windowId": s["windowId"],
        })
    return entries


# --------------------------------------------------------------------- #
# Incidents -- derived by grouping contiguous attack-majority windows
# --------------------------------------------------------------------- #
@router.get("/incidents")
def incidents():
    _require_engine()
    bursts = []
    in_burst = False
    start = label = None

    for i, m in enumerate(engine.metas[: engine.cursor + 1]):
        is_attack = m.get("attack_fraction") is not None and m["attack_fraction"] > 0.5
        if is_attack and not in_burst:
            in_burst, start, label = True, i, m.get("dominant_label")
        elif is_attack and in_burst and m.get("dominant_label") != label:
            bursts.append((start, i - 1, label))
            start, label = i, m.get("dominant_label")
        elif not is_attack and in_burst:
            bursts.append((start, i - 1, label))
            in_burst = False
    if in_burst:
        bursts.append((start, engine.cursor, label))

    now = datetime.now(timezone.utc)
    results = []
    for start_idx, end_idx, dominant_label in bursts[-10:][::-1]:
        peak_idx = max(range(start_idx, end_idx + 1), key=lambda i: engine.risk_at(i))
        risk = engine.risk_at(peak_idx)
        age_start = engine.cursor - start_idx
        age_end = max(engine.cursor - end_idx, 0)
        status = "INVESTIGATING" if age_end <= 3 else ("CONTAINED" if age_end <= 20 else "RESOLVED")
        results.append({
            "id": f"INC-W{start_idx}",
            "firstObserved": _iso(now - timedelta(seconds=age_start * cfg.WINDOW_DURATION_SEC)),
            "lastUpdated": _iso(now - timedelta(seconds=age_end * cfg.WINDOW_DURATION_SEC)),
            "riskScore": round(float(risk), 3),
            "currentStage": engine.stage_at(peak_idx),
            "forecastStage": engine.stage_at(end_idx),
            # The bundled dataset carries no source/destination IPs, so real affected
            # hosts can't be identified -- left empty rather than fabricated.
            "affectedHosts": [],
            "status": status,
            "sourceLabel": dominant_label,
        })
    return results


# --------------------------------------------------------------------- #
# Network state + attack path
# --------------------------------------------------------------------- #
@router.get("/network/state")
def network_state():
    _require_engine()
    idx = engine.cursor
    risk = engine.risk_at(idx)
    stage = engine.stage_at(idx)
    meta = engine.metas[idx]

    return {
        "timestamp": _iso(datetime.now(timezone.utc)),
        "windowId": engine.window_id(),
        "riskScore": round(float(risk), 3),
        # confidence removed -- it was just risk restated under a different key,
        # not a real calibration (see attack_stages() above for the same fix).
        "stage": {"name": stage, "status": "current", "confidence": None, "confidenceType": "not_calibrated"},
        "metrics": {
            "flowCount": meta.get("flow_count"),
            "packetCount": meta.get("total_packets"),
            "byteCount": meta.get("total_bytes"),
        },
        "features": {
            "flowRate": round(meta["raw_flow_rate_mean"], 2) if meta.get("raw_flow_rate_mean") is not None else None,
            "iatMean": round(meta["raw_iat_mean"], 3) if meta.get("raw_iat_mean") is not None else None,
        },
    }


@router.get("/network/attack-path")
def attack_path():
    _require_engine()
    risk = engine.risk_at(engine.cursor)
    stage = engine.stage_at(engine.cursor)
    dst_port = engine.metas[engine.cursor].get("avg_dst_port")

    # The bundled CIC-IDS2017 cleaned CSV carries no source/destination IP columns, so a
    # real multi-host attack path can't be reconstructed from it. This is an honestly
    # minimal 3-node chain driven by the real risk/stage output, not a fabricated
    # topology -- see README, "What's real vs. placeholder in this integration".
    nodes = [
        {"id": "external", "type": "attacker", "label": "External Traffic", "ip": None},
        {"id": "perimeter", "type": "gateway", "label": "Network Perimeter", "ip": None},
        {"id": "segment", "type": "server", "label": f"Monitored Segment — {stage}", "ip": None},
    ]
    prior_idx = max(engine.seq_len - 1, engine.cursor - 3)
    edges = [
        {
            "source": "external", "target": "perimeter", "kind": "observed",
            "riskScore": round(float(engine.risk_at(prior_idx)), 3),
            "protocol": None, "port": None,
        },
        {
            "source": "perimeter", "target": "segment",
            "kind": "predicted" if risk > 0.5 else "observed",
            "riskScore": round(float(risk), 3),
            "protocol": None, "port": round(dst_port) if dst_port is not None else None,
        },
    ]
    return {"nodes": nodes, "edges": edges}


# --------------------------------------------------------------------- #
# Explanations
# --------------------------------------------------------------------- #
@router.get("/explanations/{forecast_id}")
def explanation(forecast_id: str):
    _require_engine()
    history = engine.history()
    _, top_features = explain_risk(
        registry.model,
        lambda s: compute_risk_score(s, engine.baseline_mean, engine.baseline_std, engine.anomaly_active_mask),
        history, engine.state_feature_names, engine.baseline_mean, engine.baseline_std, top_k=5,
    )
    features = [
        {
            "name": f["feature"],
            "value": round(f["original_value"], 3),
            "contribution": round(abs(f["risk_delta"]), 4),
            "direction": "positive" if f["risk_delta"] >= 0 else "negative",
        }
        for f in top_features
    ]
    return {"forecastId": forecast_id, "method": "perturbation", "features": features}


# --------------------------------------------------------------------- #
# Telemetry -- server-paginated, from the rolling flow-level sample
# --------------------------------------------------------------------- #
# The bundled dataset has no source/destination IP, source port, or protocol columns
# (only "Destination Port" is real -- see README). These are deterministic per-row
# placeholders so the table is browsable, not measured values.
_PLACEHOLDER_PROTOCOLS = ["TCP", "UDP", "TCP", "TCP", "ICMP"]


def _synthetic_identity(idx):
    return {
        "sourceIp": f"10.{(idx // 65536) % 4}.{(idx // 256) % 256}.{idx % 256}",
        "destinationIp": f"10.{((idx + 7) // 65536) % 4}.{((idx + 7) // 256) % 256}.{(idx + 7) % 256}",
        "sourcePort": 1024 + (idx * 37) % 60000,
        "protocol": _PLACEHOLDER_PROTOCOLS[idx % len(_PLACEHOLDER_PROTOCOLS)],
    }


@router.get("/telemetry")
def telemetry(page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=500),
              protocol: Optional[str] = Query(None), minRisk: Optional[str] = Query(None)):
    _require_engine()
    now = datetime.now(timezone.utc)
    rows = list(engine.flow_sample)[::-1]  # most recently streamed first

    # The frontend's filter-clearing buttons set these to JS `undefined`, which
    # URLSearchParams serializes as the literal string "undefined" rather than
    # omitting the param -- treat that (and "null"/"") the same as "no filter".
    protocol_filter = protocol if protocol not in (None, "", "undefined", "null") else None
    min_risk_filter = None
    if minRisk not in (None, "", "undefined", "null"):
        try:
            min_risk_filter = float(minRisk)
        except ValueError:
            min_risk_filter = None

    records = []
    for pos, row in enumerate(rows):
        risk, stage = engine.flow_risk_and_stage(row["vector"])
        ident = _synthetic_identity(row["index"])
        if protocol_filter and ident["protocol"] != protocol_filter:
            continue
        if min_risk_filter is not None and risk < min_risk_filter:
            continue
        records.append({
            "id": f"flow-{row['index']}",
            "timestamp": _iso(now - timedelta(seconds=pos * 2)),
            "sourceIp": ident["sourceIp"],
            "destinationIp": ident["destinationIp"],
            "sourcePort": ident["sourcePort"],
            "destinationPort": int(row["destPort"]) if row["destPort"] is not None else None,
            "protocol": ident["protocol"],
            "flowDuration": round(row["flowDurationMs"]) if row["flowDurationMs"] is not None else None,
            "packets": row["packets"],
            "bytes": row["bytes"],
            "riskScore": round(float(risk), 3),
            "stage": stage,
        })

    total = len(records)
    start = (page - 1) * pageSize
    return {"records": records[start:start + pageSize], "total": total, "page": page, "pageSize": pageSize}
