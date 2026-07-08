from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from cashflow_guardian.security.schemas import SecurityContext, SafeError

class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    security_context: SecurityContext

class ToolExecutionDecision(BaseModel):
    allowed: bool
    permission_required: Optional[str] = None
    permission_granted: bool
    human_approval_required: bool
    policy_codes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    safe_error: Optional[SafeError] = None
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)

class WatchlistProposal(BaseModel):
    proposal_id: str
    business_id: str
    as_of_month: str
    proposed_action: str
    proposed_by: str
    proposer_role: str
    created_at: str
    expires_at: str
    risk_score: float
    risk_tier: str
    scoring_mode: str
    model_version: Optional[str] = None
    evidence_codes: List[str] = Field(default_factory=list)
    top_risk_drivers: List[str] = Field(default_factory=list)
    benchmark_summary: Dict[str, Any] = Field(default_factory=dict)
    intervention_summary: Dict[str, Any] = Field(default_factory=dict)
    human_approval_required: bool = True
    status: str = "pending"  # pending, approved, rejected, expired, cancelled
    source_provenance: Dict[str, Any] = Field(default_factory=dict)
    future_data_used: bool = False

class ApprovalDecision(BaseModel):
    decision_id: str
    proposal_id: str
    decision: str  # approve or reject
    reviewed_by: str
    reviewed_role: str
    rationale: str
    reviewed_at: str

class WatchlistActionRecord(BaseModel):
    action_id: str
    business_id: str
    status: str
    updated_at: str
    history: List[Dict[str, Any]] = Field(default_factory=list)
