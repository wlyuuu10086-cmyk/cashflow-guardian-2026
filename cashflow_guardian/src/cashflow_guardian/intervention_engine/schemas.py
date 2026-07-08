from pydantic import BaseModel, Field
from typing import List, Optional

class InterventionRecommendation(BaseModel):
    action: str
    priority: str = Field(..., description="low, medium, or high")
    description: str

class InterventionPlan(BaseModel):
    business_id: str
    as_of_month: str
    risk_tier: str
    risk_score: float
    evidence_codes: List[str]
    recommended_draft_actions: List[InterventionRecommendation]
    priority: str = Field(..., description="Overall priority: low, medium, or high")
    rationale_codes: List[str]
    human_approval_required: bool
    prohibited_actions: List[str]
    warnings: List[str] = Field(default_factory=list)
