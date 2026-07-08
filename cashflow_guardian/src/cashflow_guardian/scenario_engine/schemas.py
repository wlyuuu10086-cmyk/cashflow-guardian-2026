from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ScenarioBaseline(BaseModel):
    cash_inflow: float
    cash_outflow: float
    net_cash_flow: float
    payroll_amount: float
    debt_service: float
    collection_days: float
    repayment_burden_ratio: Optional[float] = None
    payroll_burden_ratio: Optional[float] = None
    liquidity_gap: float
    risk_score: float
    risk_tier: str

class ScenarioSimulated(BaseModel):
    cash_inflow: float
    cash_outflow: float
    net_cash_flow: float
    payroll_amount: float
    debt_service: float
    collection_days: float
    repayment_burden_ratio: Optional[float] = None
    payroll_burden_ratio: Optional[float] = None
    liquidity_gap: float
    risk_score: float
    risk_tier: str

class ScenarioResult(BaseModel):
    business_id: str
    as_of_month: str
    assumptions: Dict[str, float]
    baseline: ScenarioBaseline
    simulated: ScenarioSimulated
    risk_score_change: float
    risk_tier_change: str
    scoring_mode: str
    model_version: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    future_data_used: bool = False
    collection_delay_details: Optional[Dict[str, Any]] = None
