from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class AuditEvent(BaseModel):
    event_id: str
    timestamp: str
    request_id: str
    session_id: str
    user_id: str
    role: str
    event_type: str  # e.g., "policy_evaluation", "security_block", "proposal_created", etc.
    tool_name: Optional[str] = None
    business_id: Optional[str] = None
    decision: Optional[str] = None  # e.g., "allowed", "denied"
    policy_codes: List[str] = Field(default_factory=list)
    approval_required: bool = False
    proposal_id: Optional[str] = None
    outcome: Optional[str] = None  # e.g., "pending", "approved", "rejected"
    warnings: List[str] = Field(default_factory=list)
    redaction_applied: bool = False
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TraceStep(BaseModel):
    step_name: str  # e.g., "request_received", "policy_decision", etc.
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TraceRecord(BaseModel):
    trace_id: str
    request_id: str
    steps: List[TraceStep] = Field(default_factory=list)
