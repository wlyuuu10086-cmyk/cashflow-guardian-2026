from typing import Dict, Any, List
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.schemas import ToolExecutionDecision
from cashflow_guardian.policy.permissions import has_permission, get_required_permission_for_tool
from cashflow_guardian.policy.rules import check_prohibited_actions, check_scope_validity

def evaluate_tool_request(
    security_context: SecurityContext,
    tool_name: str,
    tool_arguments: Dict[str, Any]
) -> ToolExecutionDecision:
    """Evaluates whether a tool request is permitted by the compliance and security policies.
    
    Acts as the single gate before any tool execution.
    """
    warnings: List[str] = []
    policy_codes: List[str] = []
    
    # 1. Verify tool exists in the registry
    from cashflow_guardian.tools.registry import get_tool_registry
    registry = get_tool_registry()
    if tool_name not in registry:
        return ToolExecutionDecision(
            allowed=False,
            permission_required=None,
            permission_granted=False,
            human_approval_required=False,
            policy_codes=["POLICY_TOOL_DENIED"],
            warnings=["Tool is not registered in the system registry."],
            safe_error=None
        )
        
    entry = registry[tool_name]
    
    # 2. Check for prohibited tools or query contents
    is_prohibited, code, err_msg = check_prohibited_actions(tool_name, tool_arguments)
    if is_prohibited:
        return ToolExecutionDecision(
            allowed=False,
            permission_required=None,
            permission_granted=False,
            human_approval_required=False,
            policy_codes=[code],
            warnings=[err_msg],
            safe_error=None
        )

    # 3. Check for scope validity
    is_invalid_scope, scope_code, scope_msg = check_scope_validity(security_context, tool_arguments)
    if is_invalid_scope:
        return ToolExecutionDecision(
            allowed=False,
            permission_required=None,
            permission_granted=False,
            human_approval_required=False,
            policy_codes=[scope_code],
            warnings=[scope_msg],
            safe_error=None
        )

    # 4. Role Permission Check
    try:
        req_perm = get_required_permission_for_tool(tool_name)
    except Exception as e:
        return ToolExecutionDecision(
            allowed=False,
            permission_required=None,
            permission_granted=False,
            human_approval_required=False,
            policy_codes=["POLICY_TOOL_DENIED"],
            warnings=[str(e)],
            safe_error=None
        )
        
    granted = has_permission(security_context.role, req_perm)
    
    if not granted:
        return ToolExecutionDecision(
            allowed=False,
            permission_required=req_perm,
            permission_granted=False,
            human_approval_required=False,
            policy_codes=["POLICY_PERMISSION_MISSING"],
            warnings=[f"Role '{security_context.role}' does not possess required permission '{req_perm}'."],
            safe_error=None
        )

    # 5. Check if human approval is required for this tool
    human_approval = entry.human_approval_required

    # Prepare success decision
    policy_codes.append("POLICY_TOOL_ALLOWED")
    if human_approval:
        policy_codes.append("POLICY_HUMAN_APPROVAL_REQUIRED")

    return ToolExecutionDecision(
        allowed=True,
        permission_required=req_perm,
        permission_granted=True,
        human_approval_required=human_approval,
        policy_codes=policy_codes,
        warnings=warnings,
        safe_error=None,
        audit_metadata={"registry_permission": entry.permission}
    )
