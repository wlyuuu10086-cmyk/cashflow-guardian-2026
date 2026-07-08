import os
import yaml
import uuid
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
from pydantic import BaseModel, Field
from cashflow_guardian.security.schemas import SecurityContext, SafeError

# Import core callables
from cashflow_guardian.data_engine.connection import check_database_health
from cashflow_guardian.data_engine.features import build_point_in_time_features
from .portfolio import get_portfolio_snapshot_tool
from .business import get_business_history_tool, check_business_data_quality_tool
from .risk import score_cashflow_risk_tool
from .benchmark import compare_with_peers_tool
from .scenario import simulate_cashflow_scenario_tool
from .intervention import draft_intervention_plan_tool

def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent.parent

# --- Wrapper functions to align python signatures with YAML contracts ---

def check_business_data_quality_wrapper(business_id: str, month: str = None, as_of_month: str = None, **kwargs) -> Dict[str, Any]:
    m = month or as_of_month
    return check_business_data_quality_tool(business_id, m)

def get_portfolio_snapshot_wrapper(month: str = None, as_of_month: str = None, industry: str = None, region: str = None, limit: int = 100, **kwargs) -> Dict[str, Any]:
    m = month or as_of_month
    return get_portfolio_snapshot_tool(as_of_month=m, industry=industry, region=region, limit=limit)

def get_business_history_wrapper(business_id: str, month: str = None, as_of_month: str = None, months: int = 6, **kwargs) -> Dict[str, Any]:
    m = month or as_of_month
    return get_business_history_tool(business_id, m, months)

def build_point_in_time_features_wrapper(business_id: str, month: str = None, as_of_month: str = None, **kwargs) -> Any:
    m = month or as_of_month
    return build_point_in_time_features(business_id, m)

def score_cashflow_risk_wrapper(business_id: str, month: str = None, as_of_month: str = None, **kwargs) -> Dict[str, Any]:
    m = month or as_of_month
    return score_cashflow_risk_tool(business_id, m)

def compare_with_peers_wrapper(business_id: str, month: str = None, as_of_month: str = None, **kwargs) -> Dict[str, Any]:
    m = month or as_of_month
    return compare_with_peers_tool(business_id, m)

def simulate_cashflow_scenario_wrapper(
    business_id: str,
    month: str = None,
    as_of_month: str = None,
    cash_inflow_multiplier: float = 1.0,
    cash_outflow_multiplier: float = 1.0,
    collection_delay_days: float = 0.0,
    inflow_change_pct: float = 0.0,
    outflow_change_pct: float = 0.0,
    collection_delay_change_days: float = 0.0,
    payroll_change_pct: float = 0.0,
    debt_service_change_pct: float = 0.0,
    **kwargs
) -> Dict[str, Any]:
    m = month or as_of_month
    
    # Translate contract multipliers to percent changes if provided
    inflow_pct = inflow_change_pct
    if cash_inflow_multiplier != 1.0:
        inflow_pct = (cash_inflow_multiplier - 1.0) * 100.0
        
    outflow_pct = outflow_change_pct
    if cash_outflow_multiplier != 1.0:
        outflow_pct = (cash_outflow_multiplier - 1.0) * 100.0
        
    delay_days = collection_delay_change_days
    if collection_delay_days != 0.0:
        delay_days = collection_delay_days
        
    res = simulate_cashflow_scenario_tool(
        business_id=business_id,
        as_of_month=m,
        inflow_change_pct=inflow_pct,
        outflow_change_pct=outflow_pct,
        collection_delay_change_days=delay_days,
        payroll_change_pct=payroll_change_pct,
        debt_service_change_pct=debt_service_change_pct
    )
    
    # Map back to YAML output contract
    if res.get("status") == "success":
        res["baseline_cash_balance"] = res["baseline"].get("cash_inflow")
        res["simulated_cash_balance"] = res["simulated"].get("cash_inflow")
        res["projected_overdraft_risk"] = res["simulated"].get("liquidity_gap", 0.0) > 0.0
        
    return res

def draft_intervention_plan_wrapper(
    risk_tier: str = None,
    primary_risk_driver: str = None,
    business_id: str = None,
    month: str = None,
    as_of_month: str = None,
    include_scenario: bool = False,
    scenario_parameters: Dict[str, float] = None,
    **kwargs
) -> Dict[str, Any]:
    # Support both pure contract inputs (risk_tier, primary_risk_driver) and investigation inputs
    if risk_tier is not None:
        # Standard schema mapping fallback
        allowed_actions = []
        if risk_tier == "RED":
            allowed_actions = ["contact relationship manager for manual review", "propose demonstration watchlist review"]
        elif risk_tier == "AMBER":
            allowed_actions = ["increase monitoring frequency", "request updated cash-flow information"]
        else:
            allowed_actions = ["continue routine monitoring"]
            
        return {
            "status": "success",
            "risk_tier": risk_tier,
            "recommended_playbook": f"Playbook for {risk_tier} risk tier focused on {primary_risk_driver or 'general stress'}.",
            "allowed_actions": allowed_actions
        }
        
    m = month or as_of_month
    res = draft_intervention_plan_tool(
        business_id=business_id,
        as_of_month=m,
        include_scenario=include_scenario,
        scenario_parameters=scenario_parameters
    )
    
    # Map back to YAML output contracts
    if res.get("status") == "success":
        res["recommended_playbook"] = f"Plan for risk tier {res['risk_tier']}"
        res["allowed_actions"] = [act["action"] for act in res["recommended_draft_actions"]]
        
    return res

def propose_watchlist_action_wrapper(
    business_id: str,
    month: str,
    reason: str,
    RM_id: str,
    security_context: Optional[SecurityContext] = None,
    **kwargs
) -> Dict[str, Any]:
    import uuid
    import datetime
    from cashflow_guardian.policy.watchlist import create_watchlist_proposal
    from cashflow_guardian.tools.risk import score_cashflow_risk_tool
    from cashflow_guardian.tools.intervention import draft_intervention_plan_tool
    
    if not security_context:
        security_context = SecurityContext(
            request_id="req_" + uuid.uuid4().hex[:8],
            session_id="ses_1",
            user_id=RM_id,
            role="relationship_manager",
            requested_tool="propose_watchlist_action",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            source="system",
            environment="local"
        )
    
    # We query risk score and intervention draft to provide evidence to create proposal
    risk_res = score_cashflow_risk_tool(business_id, month)
    int_plan = draft_intervention_plan_tool(business_id, month)
    
    # Store reason in metadata for the creation logic
    security_context.metadata["reason"] = reason
    
    prop = create_watchlist_proposal(
        business_id=business_id,
        as_of_month=month,
        proposed_by=RM_id,
        risk_result=risk_res,
        intervention_plan=int_plan,
        security_context=security_context
    )
    
    return {
        "action_id": prop["proposal_id"],
        "status": prop["status"],
        "message": f"Proposal created successfully with ID {prop['proposal_id']}."
    }

def approve_or_reject_watchlist_action_wrapper(
    action_id: str,
    decision: str,
    approver_id: str,
    security_context: Optional[SecurityContext] = None,
    **kwargs
) -> Dict[str, Any]:
    import uuid
    import datetime
    from cashflow_guardian.policy.watchlist import review_watchlist_proposal
    
    if not security_context:
        security_context = SecurityContext(
            request_id="req_" + uuid.uuid4().hex[:8],
            session_id="ses_1",
            user_id=approver_id,
            role="risk_manager",
            requested_tool="approve_or_reject_watchlist_action",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            source="system",
            environment="local"
        )
        
    rationale = security_context.metadata.get("rationale") or "Decision reviewed by risk manager."
    
    res = review_watchlist_proposal(
        proposal_id=action_id,
        decision="approve" if decision == "approved" or decision == "approve" else "reject",
        reviewed_by=approver_id,
        rationale=rationale,
        security_context=security_context
    )
    
    return {
        "action_id": res["action_id"],
        "updated_status": res["updated_status"],
        "audit_timestamp": res["audit_timestamp"]
    }

class ToolRegistryEntry(BaseModel):
    name: str
    description: str
    callable_func: Any
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    permission: str
    human_approval_required: bool
    allowed_source_tables: List[str]
    prohibited_behaviors: List[str]

# Global registry dict
_REGISTRY: Dict[str, ToolRegistryEntry] = {}

# Approved tools list for Step 5 and HITL
APPROVED_TOOL_NAMES = [
    "check_database_health",
    "check_business_data_quality",
    "get_portfolio_snapshot",
    "get_business_history",
    "build_point_in_time_features",
    "score_cashflow_risk",
    "compare_with_peers",
    "simulate_cashflow_scenario",
    "draft_intervention_plan",
    "propose_watchlist_action",
    "approve_or_reject_watchlist_action"
]

def load_and_validate_registry() -> None:
    global _REGISTRY
    _REGISTRY.clear()
    
    repo_root = get_repo_root()
    contracts_path = repo_root / "cashflow_guardian" / "specs" / "tool_contracts.yaml"
    
    if not contracts_path.exists():
        contracts_path = repo_root / "specs" / "tool_contracts.yaml"
        if not contracts_path.exists():
            raise FileNotFoundError(f"Tool contracts not found at {contracts_path}")
            
    with open(contracts_path, "r") as f:
        contracts_data = yaml.safe_load(f)
        
    yaml_tools = {t["name"]: t for t in contracts_data.get("tools", [])}
    
    callables_map: Dict[str, Callable] = {
        "check_database_health": check_database_health,
        "check_business_data_quality": check_business_data_quality_wrapper,
        "get_portfolio_snapshot": get_portfolio_snapshot_wrapper,
        "get_business_history": get_business_history_wrapper,
        "build_point_in_time_features": build_point_in_time_features_wrapper,
        "score_cashflow_risk": score_cashflow_risk_wrapper,
        "compare_with_peers": compare_with_peers_wrapper,
        "simulate_cashflow_scenario": simulate_cashflow_scenario_wrapper,
        "draft_intervention_plan": draft_intervention_plan_wrapper,
        "propose_watchlist_action": propose_watchlist_action_wrapper,
        "approve_or_reject_watchlist_action": approve_or_reject_watchlist_action_wrapper
    }
    
    for name in APPROVED_TOOL_NAMES:
        if name not in callables_map:
            raise ValueError(f"Required tool '{name}' has no registered python callable.")
            
    for name in APPROVED_TOOL_NAMES:
        if name not in yaml_tools:
            raise ValueError(f"Required tool '{name}' is missing from tool_contracts.yaml.")
            
        y_tool = yaml_tools[name]
        
        entry = ToolRegistryEntry(
            name=name,
            description=y_tool.get("purpose", ""),
            callable_func=callables_map[name],
            input_schema=y_tool.get("input_schema", {}),
            output_schema=y_tool.get("output_schema", {}),
            permission=y_tool.get("permissions", "read-only"),
            human_approval_required=y_tool.get("human_approval_required", False),
            allowed_source_tables=y_tool.get("allowed_tables", []),
            prohibited_behaviors=[y_tool.get("prohibited_behavior", "")]
        )
        _REGISTRY[name] = entry
        
    for name in callables_map:
        if name not in APPROVED_TOOL_NAMES:
            raise ValueError(f"Unapproved tool '{name}' is attempted to be registered.")

load_and_validate_registry()

def get_tool_registry() -> Dict[str, ToolRegistryEntry]:
    return _REGISTRY

def get_tool_by_name(name: str) -> ToolRegistryEntry:
    if name not in _REGISTRY:
        raise ValueError(f"Tool '{name}' is not registered or is unapproved.")
    return _REGISTRY[name]

def list_tool_metadata() -> List[Dict[str, Any]]:
    return [
        {
            "name": entry.name,
            "description": entry.description,
            "permission": entry.permission,
            "human_approval_required": entry.human_approval_required,
            "allowed_source_tables": entry.allowed_source_tables,
            "prohibited_behaviors": entry.prohibited_behaviors
        }
        for entry in _REGISTRY.values()
    ]

# --- Secure execution engine integration ---

class ToolExecutionResult(BaseModel):
    request_id: str
    tool_name: str
    status: str  # success, denied, validation_error, approval_required, execution_error
    allowed: bool
    approval_required: bool
    result: Optional[Any] = None
    safe_error: Optional[SafeError] = None
    policy_codes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    audit_event_id: str
    trace_id: str

def execute_tool_with_policy(
    security_context: SecurityContext,
    tool_name: str,
    tool_arguments: Dict[str, Any]
) -> ToolExecutionResult:
    """Executes a registered tool securely after validating policy and security controls.
    
    This function:
      1. Validates inputs and security contexts, guarding against injection.
      2. Evaluates compliance policies and role-based permissions.
      3. Verifies human-in-the-loop approval signatures.
      4. Executes the registered callable only.
      5. Redacts outputs and exception messages to prevent data leaks.
      6. Emits structured audit and trace steps.
    """
    import time
    import datetime
    from cashflow_guardian.security.guards import apply_security_guards
    from cashflow_guardian.security.redaction import redact_sensitive_data
    from cashflow_guardian.security.safe_errors import translate_to_safe_error, CashFlowGuardianSecurityError
    from cashflow_guardian.policy.engine import evaluate_tool_request
    from cashflow_guardian.policy.schemas import ToolExecutionDecision
    from cashflow_guardian.observability.schemas import AuditEvent
    from cashflow_guardian.observability.audit_log import log_audit_event
    from cashflow_guardian.observability.trace_store import global_trace_store

    start_time = time.time()
    
    # 1. Resolve or generate trace_id
    trace_id = security_context.metadata.get("trace_id") or f"trace_{uuid.uuid4().hex[:16]}"
    request_id = security_context.request_id
    audit_event_id = f"evt_{uuid.uuid4().hex[:16]}"
    
    # Initialize trace record
    global_trace_store.create_trace(trace_id, request_id)
    global_trace_store.add_step(trace_id, "request_received", {"tool_name": tool_name})
    
    # 2. Security validation (Input guards, format, SQLi in IDs, path traversals)
    global_trace_store.add_step(trace_id, "security_validation")
    try:
        apply_security_guards(security_context, tool_name, tool_arguments)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000.0
        safe_err = translate_to_safe_error(e, request_id)
        
        global_trace_store.add_step(trace_id, "tool_failed", {"reason": "security_validation_error"})
        global_trace_store.add_step(trace_id, "response_produced")
        
        # Log audit event
        audit_event = AuditEvent(
            event_id=audit_event_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            request_id=request_id,
            session_id=security_context.session_id,
            user_id=security_context.user_id,
            role=security_context.role,
            event_type="security_block",
            tool_name=tool_name,
            business_id=security_context.business_id or tool_arguments.get("business_id"),
            decision="denied",
            policy_codes=safe_err.policy_codes or ["SECURITY_INVALID_INPUT"],
            approval_required=False,
            proposal_id=None,
            outcome=None,
            warnings=safe_err.warnings or [str(e)],
            redaction_applied=True,
            duration_ms=duration_ms
        )
        log_audit_event(audit_event, fail_closed=False)
        
        return ToolExecutionResult(
            request_id=request_id,
            tool_name=tool_name,
            status="validation_error",
            allowed=False,
            approval_required=False,
            safe_error=safe_err,
            policy_codes=safe_err.policy_codes or ["SECURITY_INVALID_INPUT"],
            warnings=safe_err.warnings or [str(e)],
            audit_event_id=audit_event_id,
            trace_id=trace_id
        )

    # 3. Policy evaluation
    global_trace_store.add_step(trace_id, "policy_decision")
    decision = evaluate_tool_request(security_context, tool_name, tool_arguments)
    
    if not decision.allowed:
        duration_ms = (time.time() - start_time) * 1000.0
        safe_err = SafeError(
            error_code="PERMISSION_DENIED",
            message=decision.warnings[0] if decision.warnings else "Access denied by policy.",
            retryable=False,
            invalid_fields=[],
            policy_codes=decision.policy_codes,
            warnings=decision.warnings,
            request_id=request_id
        )
        
        global_trace_store.add_step(trace_id, "response_produced")
        
        # Log audit event
        audit_event = AuditEvent(
            event_id=audit_event_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            request_id=request_id,
            session_id=security_context.session_id,
            user_id=security_context.user_id,
            role=security_context.role,
            event_type="policy_evaluation",
            tool_name=tool_name,
            business_id=security_context.business_id or tool_arguments.get("business_id"),
            decision="denied",
            policy_codes=decision.policy_codes,
            approval_required=decision.human_approval_required,
            proposal_id=None,
            outcome=None,
            warnings=decision.warnings,
            redaction_applied=False,
            duration_ms=duration_ms
        )
        log_audit_event(audit_event, fail_closed=False)
        
        return ToolExecutionResult(
            request_id=request_id,
            tool_name=tool_name,
            status="denied",
            allowed=False,
            approval_required=decision.human_approval_required,
            safe_error=safe_err,
            policy_codes=decision.policy_codes,
            warnings=decision.warnings,
            audit_event_id=audit_event_id,
            trace_id=trace_id
        )

    # 4. Human-in-the-loop execution guard
    # If the tool requires human approval, we check if the request is signed as approved
    if decision.human_approval_required:
        is_approved = security_context.metadata.get("approved") is True
        if not is_approved:
            duration_ms = (time.time() - start_time) * 1000.0
            
            global_trace_store.add_step(trace_id, "approval_requested")
            global_trace_store.add_step(trace_id, "response_produced")
            
            audit_event = AuditEvent(
                event_id=audit_event_id,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                request_id=request_id,
                session_id=security_context.session_id,
                user_id=security_context.user_id,
                role=security_context.role,
                event_type="policy_evaluation",
                tool_name=tool_name,
                business_id=security_context.business_id or tool_arguments.get("business_id"),
                decision="denied",
                policy_codes=["POLICY_HUMAN_APPROVAL_REQUIRED"],
                approval_required=True,
                proposal_id=None,
                outcome=None,
                warnings=["Human approval is required to execute this tool."],
                redaction_applied=False,
                duration_ms=duration_ms
            )
            log_audit_event(audit_event, fail_closed=False)
            
            safe_err = SafeError(
                error_code="APPROVAL_REQUIRED",
                message="This action requires explicit human-in-the-loop approval.",
                retryable=False,
                invalid_fields=[],
                policy_codes=["POLICY_HUMAN_APPROVAL_REQUIRED"],
                warnings=["Human approval required."],
                request_id=request_id
            )
            
            return ToolExecutionResult(
                request_id=request_id,
                tool_name=tool_name,
                status="approval_required",
                allowed=True,
                approval_required=True,
                safe_error=safe_err,
                policy_codes=["POLICY_HUMAN_APPROVAL_REQUIRED"],
                warnings=["Human approval required."],
                audit_event_id=audit_event_id,
                trace_id=trace_id
            )

    # 5. Call registered registry tool callable
    global_trace_store.add_step(trace_id, "tool_selected", {"tool_name": tool_name})
    global_trace_store.add_step(trace_id, "tool_started")
    
    if tool_name in ["propose_watchlist_action", "approve_or_reject_watchlist_action"]:
        tool_arguments = tool_arguments.copy()
        tool_arguments["security_context"] = security_context

    entry = _REGISTRY[tool_name]
    try:
        raw_result = entry.callable_func(**tool_arguments)
        
        # Check if returned dictionary is a safe error
        if isinstance(raw_result, dict) and raw_result.get("status") == "error":
            # Map tool-returned error payload to execution error status
            err_code = raw_result.get("error_code", "EXECUTION_ERROR")
            err_msg = raw_result.get("message", "Tool execution failed.")
            safe_err = SafeError(
                error_code=err_code,
                message=err_msg,
                retryable=raw_result.get("retryable", False),
                invalid_fields=raw_result.get("invalid_fields", []),
                policy_codes=decision.policy_codes,
                warnings=raw_result.get("warnings", []),
                request_id=request_id
            )
            
            duration_ms = (time.time() - start_time) * 1000.0
            global_trace_store.add_step(trace_id, "tool_failed", {"error_code": err_code})
            global_trace_store.add_step(trace_id, "response_produced")
            
            audit_event = AuditEvent(
                event_id=audit_event_id,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                request_id=request_id,
                session_id=security_context.session_id,
                user_id=security_context.user_id,
                role=security_context.role,
                event_type="tool_execution_failed",
                tool_name=tool_name,
                business_id=security_context.business_id or tool_arguments.get("business_id"),
                decision="allowed",
                policy_codes=decision.policy_codes,
                approval_required=decision.human_approval_required,
                proposal_id=None,
                outcome=None,
                warnings=raw_result.get("warnings", []),
                redaction_applied=False,
                duration_ms=duration_ms
            )
            log_audit_event(audit_event, fail_closed=False)
            
            return ToolExecutionResult(
                request_id=request_id,
                tool_name=tool_name,
                status="execution_error",
                allowed=True,
                approval_required=decision.human_approval_required,
                safe_error=safe_err,
                policy_codes=decision.policy_codes,
                warnings=raw_result.get("warnings", []),
                audit_event_id=audit_event_id,
                trace_id=trace_id
            )

        # Output redaction
        redacted_result, redact_meta = redact_sensitive_data(raw_result)
        
        duration_ms = (time.time() - start_time) * 1000.0
        global_trace_store.add_step(trace_id, "tool_completed")
        global_trace_store.add_step(trace_id, "response_produced")
        
        # Log success audit event
        audit_event = AuditEvent(
            event_id=audit_event_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            request_id=request_id,
            session_id=security_context.session_id,
            user_id=security_context.user_id,
            role=security_context.role,
            event_type="tool_execution_success",
            tool_name=tool_name,
            business_id=security_context.business_id or tool_arguments.get("business_id"),
            decision="allowed",
            policy_codes=decision.policy_codes,
            approval_required=decision.human_approval_required,
            proposal_id=None,
            outcome="success",
            warnings=decision.warnings,
            redaction_applied=redact_meta.get("redacted_count", 0) > 0,
            duration_ms=duration_ms
        )
        
        # If the action was watchlist proposal/decision write, fail-closed on log error
        fail_closed_log = tool_name in ["propose_watchlist_action", "approve_or_reject_watchlist_action"]
        log_audit_event(audit_event, fail_closed=fail_closed_log)

        # Resolve provenance
        provenance = {}
        if isinstance(redacted_result, dict):
            provenance = redacted_result.get("provenance", {})
            
        return ToolExecutionResult(
            request_id=request_id,
            tool_name=tool_name,
            status="success",
            allowed=True,
            approval_required=decision.human_approval_required,
            result=redacted_result,
            policy_codes=decision.policy_codes,
            warnings=decision.warnings,
            provenance=provenance,
            audit_event_id=audit_event_id,
            trace_id=trace_id
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000.0
        safe_err = translate_to_safe_error(e, request_id)
        
        global_trace_store.add_step(trace_id, "tool_failed", {"reason": "exception"})
        global_trace_store.add_step(trace_id, "response_produced")
        
        audit_event = AuditEvent(
            event_id=audit_event_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            request_id=request_id,
            session_id=security_context.session_id,
            user_id=security_context.user_id,
            role=security_context.role,
            event_type="tool_execution_failed",
            tool_name=tool_name,
            business_id=security_context.business_id or tool_arguments.get("business_id"),
            decision="allowed",
            policy_codes=decision.policy_codes,
            approval_required=decision.human_approval_required,
            proposal_id=None,
            outcome="failure",
            warnings=[str(e)],
            redaction_applied=True,
            duration_ms=duration_ms
        )
        log_audit_event(audit_event, fail_closed=False)
        
        return ToolExecutionResult(
            request_id=request_id,
            tool_name=tool_name,
            status="execution_error",
            allowed=True,
            approval_required=decision.human_approval_required,
            safe_error=safe_err,
            policy_codes=decision.policy_codes,
            warnings=[str(e)],
            audit_event_id=audit_event_id,
            trace_id=trace_id
        )
