import inspect

from cashflow_guardian.agent.tool_adapter import (
    MODEL_SAFE_TOOL_NAMES,
    get_model_safe_tools,
)
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.tools.registry import ToolExecutionResult


def _context() -> SecurityContext:
    return SecurityContext(
        request_id="req_test",
        session_id="sess_test",
        user_id="ambient:test",
        role="system_agent",
        requested_tool="test",
        business_id="B00001",
        as_of_month="2025-06",
        timestamp="2026-07-03T00:00:00Z",
        source="test",
        environment="test",
        metadata={"trace_id": "trace_test"},
    )


def test_model_safe_tools_exclude_privileged_actions():
    names = set(MODEL_SAFE_TOOL_NAMES)

    assert "approve_or_reject_watchlist_action" not in names
    assert "propose_watchlist_action" not in names


def test_model_safe_tools_do_not_expose_identity_parameters():
    forbidden = {"role", "user_id", "permissions", "security_context", "approved", "reviewer_id"}

    for tool in get_model_safe_tools(_context()):
        params = set(inspect.signature(tool).parameters)
        assert params.isdisjoint(forbidden)


def test_model_safe_tools_call_execute_tool_with_policy(monkeypatch):
    calls = []

    def fake_execute(security_context, tool_name, tool_arguments):
        calls.append((security_context, tool_name, tool_arguments))
        return ToolExecutionResult(
            request_id=security_context.request_id,
            tool_name=tool_name,
            status="success",
            allowed=True,
            approval_required=False,
            result={"status": "success"},
            policy_codes=["POLICY_TOOL_ALLOWED"],
            warnings=[],
            provenance={},
            audit_event_id=f"evt_{tool_name}",
            trace_id=security_context.metadata["trace_id"],
        )

    monkeypatch.setattr("cashflow_guardian.agent.tool_adapter.execute_tool_with_policy", fake_execute)

    tools = {tool.__name__: tool for tool in get_model_safe_tools(_context())}
    tools["check_business_data_quality"]("B00001", "2025-06")
    tools["get_portfolio_snapshot"]("2025-06", 5)
    tools["get_business_history"]("B00001", "2025-06")
    tools["score_cashflow_risk"]("B00001", "2025-06")
    tools["compare_with_peers"]("B00001", "2025-06")
    tools["simulate_cashflow_scenario"]("B00001", "2025-06", -20.0, 0.0, 15.0)
    tools["draft_intervention_plan"]("B00001", "2025-06")

    assert [call[1] for call in calls] == list(MODEL_SAFE_TOOL_NAMES)
    assert all(call[0].role == "system_agent" for call in calls)
