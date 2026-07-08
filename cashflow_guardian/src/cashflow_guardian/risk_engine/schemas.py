from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class FeatureContribution(BaseModel):
    feature_name: str
    contribution_value: float

class RiskScoreResult(BaseModel):
    business_id: str
    month: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str # RED, AMBER, GREEN, CRITICAL
    model_version: Optional[str]
    scoring_mode: str # "ml_model" or "rule_based_fallback"
    model_prediction_available: bool
    risk_score_type: str # "calibrated" or "heuristic"
    feature_contributions: List[FeatureContribution]
    local_contextual_evidence: Dict[str, Any]
    warnings: List[str] = []

class RiskExplanation(BaseModel):
    business_id: str
    month: str
    risk_score: float
    risk_tier: str
    observed_facts: Dict[str, Any]
    deterministic_metrics: Dict[str, Any]
    model_predictions: Dict[str, Any]
    local_contributions: List[FeatureContribution]
    interpretations: List[str]
