from typing import Dict, Any, List, Tuple
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.permissions import get_required_permission_for_tool

# List of strictly forbidden actions/tools
FORBIDDEN_TOOLS = [
    "database_write",
    "execute_sql",
    "run_sql",
    "raw_query",
    "send_email",
    "change_credit_limit",
    "approve_loan",
    "reject_loan",
    "freeze_account",
    "execute_collections"
]

def check_prohibited_actions(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str, str]:
    """Checks if the request violates prohibited actions.
    
    Returns:
        Tuple[is_prohibited (bool), policy_code (str), error_message (str)]
    """
    # 1. Block forbidden tool names
    if tool_name in FORBIDDEN_TOOLS:
        return True, "POLICY_TOOL_DENIED", f"Action blocked: Tool '{tool_name}' is strictly prohibited."
        
    # 2. Block prohibited tool arguments
    # Look for arguments requesting database writes, SQL execution, or future outcomes
    for key, val in arguments.items():
        if isinstance(val, str):
            val_upper = val.upper()
            
            # Check for SQL keywords or query attempts if any argument looks like SQL
            if key in ["sql", "query"] or "SELECT " in val_upper or "UNION " in val_upper:
                return True, "POLICY_ARBITRARY_SQL_BLOCKED", "Action blocked: Arbitrary SQL execution is prohibited."
                
            if "INSERT " in val_upper or "UPDATE " in val_upper or "DELETE " in val_upper or "DROP " in val_upper:
                return True, "POLICY_DATABASE_WRITE_BLOCKED", "Action blocked: Database write operations are prohibited."
                
            # Exclude outcome labels or future outcomes
            if "BUSINESS_MONTHLY_OUTCOMES" in val_upper:
                return True, "POLICY_FUTURE_DATA_BLOCKED", "Action blocked: Access to the business outcomes table is prohibited."
                
            if "FUTURE_60D_" in val_upper:
                return True, "POLICY_FUTURE_DATA_BLOCKED", "Action blocked: Access to future outcome columns is prohibited."

    return False, "", ""

def check_scope_validity(security_context: SecurityContext, arguments: Dict[str, Any]) -> Tuple[bool, str, str]:
    """Ensures business_id and month scopes are valid and match across context and arguments.
    
    Returns:
        Tuple[is_invalid (bool), policy_code (str), error_message (str)]
    """
    # Check business_id alignment if present in both
    ctx_biz = security_context.business_id
    arg_biz = arguments.get("business_id")
    
    if ctx_biz and arg_biz and ctx_biz != arg_biz:
        return True, "POLICY_TOOL_DENIED", f"Scope violation: SecurityContext business_id '{ctx_biz}' does not match tool argument business_id '{arg_biz}'."

    # Check month alignment if present in both
    ctx_month = security_context.as_of_month
    arg_month = arguments.get("month") or arguments.get("as_of_month")
    
    if ctx_month and arg_month and ctx_month != arg_month:
        return True, "POLICY_TOOL_DENIED", f"Scope violation: SecurityContext as_of_month '{ctx_month}' does not match tool argument month '{arg_month}'."

    return False, "", ""
