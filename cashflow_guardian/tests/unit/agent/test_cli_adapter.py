import inspect
from unittest.mock import patch

from agents_cli_agent.agent import root_agent, cli_security_context
from cashflow_guardian.agent.tool_adapter import MODEL_SAFE_TOOL_NAMES, MODEL_FORBIDDEN_TOOL_NAMES


def test_root_agent_imports_and_has_safe_tools():
    """Verify that root_agent loads and contains at least one model-safe tool."""
    assert root_agent is not None
    assert root_agent.name == "cashflow_guardian_agent"
    assert len(root_agent.tools) > 0


def test_exposed_tools_are_safe_and_mutation_free():
    """Verify that all exposed tools are in the allowlist and no forbidden tools are exposed."""
    exposed_names = [tool.__name__ for tool in root_agent.tools]
    
    # All exposed tools must be in the model-safe allowlist
    for name in exposed_names:
        assert name in MODEL_SAFE_TOOL_NAMES, f"Tool '{name}' is not in the safe allowlist."
        
    # Forbidden watchlist mutation tools must be completely absent
    for name in MODEL_FORBIDDEN_TOOL_NAMES:
        assert name not in exposed_names, f"Privileged tool '{name}' is exposed to CLI agent."


def test_eval_security_context_is_fixed_in_code():
    """Verify that the evaluation SecurityContext is fixed to the analyst role."""
    assert cli_security_context is not None
    assert cli_security_context.role == "analyst"
    assert cli_security_context.user_id == "cli_user"
    assert cli_security_context.session_id == "cli_session"
    assert cli_security_context.environment == "local"


def test_tool_signatures_prevent_prompt_control():
    """Verify that tool parameters do not expose privileged trusted fields to the model prompt."""
    forbidden_params = {
        "role",
        "user_id",
        "permissions",
        "security_context",
        "approved",
        "approval_status",
        "reviewer_id",
    }
    for tool in root_agent.tools:
        params = set(inspect.signature(tool).parameters)
        overlap = params & forbidden_params
        assert not overlap, f"Tool '{tool.__name__}' exposes trusted parameters: {overlap}"


def test_tools_execute_through_policy_engine():
    """Verify that executing any exposed tool routes through execute_tool_with_policy."""
    with patch("cashflow_guardian.agent.tool_adapter.execute_tool_with_policy") as mock_execute:
        # Retrieve the check_business_data_quality tool
        target_tool = None
        for tool in root_agent.tools:
            if tool.__name__ == "check_business_data_quality":
                target_tool = tool
                break
                
        assert target_tool is not None, "check_business_data_quality tool is missing"
        
        # Invoke the tool
        target_tool(business_id="B00001", as_of_month="2025-06")
        
        # Verify execute_tool_with_policy was called with the fixed CLI security context
        mock_execute.assert_called_once()
        called_ctx = mock_execute.call_args[0][0]
        called_tool = mock_execute.call_args[0][1]
        called_args = mock_execute.call_args[0][2]
        
        assert called_ctx.role == "analyst"
        assert called_ctx.user_id == "cli_user"
        assert called_tool == "check_business_data_quality"
        assert called_args == {"business_id": "B00001", "as_of_month": "2025-06"}
