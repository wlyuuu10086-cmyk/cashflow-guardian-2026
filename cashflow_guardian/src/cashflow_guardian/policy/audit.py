from typing import Dict, Any, Optional
import datetime
import uuid
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.schemas import ToolExecutionDecision
from cashflow_guardian.observability.schemas import AuditEvent

def log_policy_evaluation(
    security_context: SecurityContext,
    tool_name: str,
    tool_arguments: Dict[str, Any],
    decision: ToolExecutionDecision,
    duration_ms: Optional[float] = None
) -> None:
    """Helper to construct and write an AuditEvent for a policy evaluation."""
    from cashflow_guardian.observability.audit_log import log_audit_event

    # 1. Map to AuditEvent
    event = AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:16]}",
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        request_id=security_context.request_id,
        session_id=security_context.session_id,
        user_id=security_context.user_id,
        role=security_context.role,
        event_type="policy_evaluation",
        tool_name=tool_name,
        business_id=security_context.business_id or tool_arguments.get("business_id"),
        decision="allowed" if decision.allowed else "denied",
        policy_codes=decision.policy_codes,
        approval_required=decision.human_approval_required,
        proposal_id=None,
        outcome=None,
        warnings=decision.warnings,
        redaction_applied=False,  # Evaluated later
        duration_ms=duration_ms
    )
    
    # 2. Persist
    log_audit_event(event)

def log_hitl_audit_event(
    security_context: SecurityContext,
    event_type: str,  # "proposal_created", "proposal_approved", "proposal_rejected"
    proposal_id: str,
    business_id: str,
    decision_status: str,  # "pending", "approved", "rejected"
    policy_codes: list,
    duration_ms: Optional[float] = None
) -> None:
    """Helper to construct and write an AuditEvent for HITL proposal states."""
    from cashflow_guardian.observability.audit_log import log_audit_event

    event = AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:16]}",
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        request_id=security_context.request_id,
        session_id=security_context.session_id,
        user_id=security_context.user_id,
        role=security_context.role,
        event_type=event_type,
        tool_name="watchlist_workflow",
        business_id=business_id,
        decision="allowed",
        policy_codes=policy_codes,
        approval_required=True,
        proposal_id=proposal_id,
        outcome=decision_status,
        warnings=[],
        redaction_applied=False,
        duration_ms=duration_ms
    )
    log_audit_event(event)
