from typing import Dict, Any
from .schemas import SecurityContext
from .validation import validate_input_parameters, SecurityValidationError
from .prompt_injection import assess_prompt_injection
from .safe_errors import CashFlowGuardianSecurityError

def apply_security_guards(security_context: SecurityContext, tool_name: str, arguments: Dict[str, Any]) -> None:
    """Orchestrates all security validation checks on a tool execution request.
    
    Performs:
      1. Validation of the security context structure and fields.
      2. Validation of the inputs (SQLi in IDs, traversals, NaN/infinity, path checks).
      3. Non-destructive prompt-injection scanning on natural language text fields.
      
    Raises CashFlowGuardianSecurityError if any check fails.
    """
    # 1. Validate security context fields
    if not security_context.request_id or not security_context.user_id or not security_context.role:
        raise CashFlowGuardianSecurityError(
            "Invalid SecurityContext: request_id, user_id, and role are required.",
            error_code="SECURITY_VALIDATION_ERROR",
            policy_codes=["SECURITY_INVALID_INPUT"]
        )

    # 2. Run input parameters validations
    try:
        validate_input_parameters(tool_name, arguments)
    except SecurityValidationError as e:
        raise CashFlowGuardianSecurityError(
            str(e),
            error_code="SECURITY_VALIDATION_ERROR",
            policy_codes=["SECURITY_INVALID_INPUT"]
        )

    # 3. Assess prompt injection in text fields
    # Loop over all string arguments to assess injection risk
    for key, val in arguments.items():
        if isinstance(val, str) and key not in ["business_id", "month", "as_of_month", "RM_id", "action_id", "proposal_id"]:
            assessment = assess_prompt_injection(val)
            if assessment.detected:
                raise CashFlowGuardianSecurityError(
                    f"Security Block: Unsafe content detected in parameter '{key}'. Matched: {', '.join(assessment.matched_patterns)}",
                    error_code="SECURITY_INJECTION_DETECTED",
                    policy_codes=["SECURITY_INJECTION_DETECTED"]
                )
