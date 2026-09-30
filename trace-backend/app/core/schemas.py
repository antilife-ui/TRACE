from pydantic import BaseModel
from typing import List, Optional


class DrivingFeature(BaseModel):
    feature: str
    original_value: float
    perturbed_value: float
    risk_delta: float


class ForecastRequest(BaseModel):
    state_history: List[List[float]]
    K: int = 5


class ForecastResponse(BaseModel):
    risk_score: float
    forecast_horizon: int
    predicted_stage: str
    driving_features: List[DrivingFeature]
    predicted_states: List[List[float]]


class RolloutRequest(BaseModel):
    state_history: List[List[float]]
    K: int = 5


class RolloutResponse(BaseModel):
    predicted_states: List[List[float]]
    per_step_risk: List[float]


class ExplainRequest(BaseModel):
    state_history: List[List[float]]
    top_k: int = 5


class ExplainResponse(BaseModel):
    base_risk: float
    driving_features: List[DrivingFeature]


class ModelStatusResponse(BaseModel):
    loaded: bool
    input_size: Optional[int] = None
    hidden_size: Optional[int] = None
    seq_len: Optional[int] = None
    trained_at: Optional[str] = None
    mode: Optional[str] = None
