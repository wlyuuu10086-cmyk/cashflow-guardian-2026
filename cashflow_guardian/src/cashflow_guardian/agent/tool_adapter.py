from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, Iterable, List

from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.tools.registry import ToolExecutionResult, execute_tool_with_policy

MODEL_SAFE_TOOL_NAMES = (
    "check_business_data_quality",
    "get_portfolio_snapshot",
    "get_business_history",
    "score_cashflow_risk",
    "compare_with_peers",
    "simulate_cashflow_scenario",
    "draft_intervention_plan",
)

MODEL_FORBIDDEN_TOOL_NAMES = (
    "propose_watchlist_action",
    "approve_or_reject_watchlist_action",
)


def _safe_result(result: ToolExecutionResult) -> Dict[str, Any]:
    payload = result.model_dump(mode="json")
    if payload.get("safe_error"):
        payload["result"] = None
    return payload


def _execute(
    security_context: SecurityContext,
    tool_name: str,
    tool_arguments: Dict[str, Any],
) -> Dict[str, Any]:
    result = execute_tool_with_policy(security_context, tool_name, tool_arguments)
    return _safe_result(result)


def get_model_safe_tool_specs() -> List[Dict[str, Any]]:
    """Returns testable metadata for tools that may be shown to an ADK model."""
    return [
        {
            "name": "check_business_data_quality",
            "internal_tool_name": "check_business_data_quality",
            "parameters": ["business_id", "as_of_month"],
        },
        {
            "name": "get_portfolio_snapshot",
            "internal_tool_name": "get_portfolio_snapshot",
            "parameters": ["as_of_month", "limit"],
        },
        {
            "name": "get_business_history",
            "internal_tool_name": "get_business_history",
            "parameters": ["business_id", "as_of_month"],
        },
        {
            "name": "score_cashflow_risk",
            "internal_tool_name": "score_cashflow_risk",
            "parameters": ["business_id", "as_of_month"],
        },
        {
            "name": "compare_with_peers",
            "internal_tool_name": "compare_with_peers",
            "parameters": ["business_id", "as_of_month"],
        },
        {
            "name": "simulate_cashflow_scenario",
            "internal_tool_name": "simulate_cashflow_scenario",
            "parameters": [
                "business_id",
                "as_of_month",
                "inflow_change_pct",
                "outflow_change_pct",
                "collection_delay_change_days",
            ],
        },
        {
            "name": "draft_intervention_plan",
            "internal_tool_name": "draft_intervention_plan",
            "parameters": ["business_id", "as_of_month"],
        },
    ]


def get_model_safe_tools(security_context: SecurityContext) -> List[Callable[..., Dict[str, Any]]]:
    """Builds ADK-compatible tools bound to trusted, non-model-controlled context."""

    def check_business_data_quality(business_id: str, as_of_month: str) -> Dict[str, Any]:
        """Check whether a business has sufficient data for analysis."""
        return _execute(
            security_context,
            "check_business_data_quality",
            {"business_id": business_id, "as_of_month": as_of_month},
        )

    def get_portfolio_snapshot(as_of_month: str, limit: int) -> Dict[str, Any]:
        """Retrieve a bounded portfolio snapshot for an as-of month."""
        return _execute(
            security_context,
            "get_portfolio_snapshot",
            {"as_of_month": as_of_month, "limit": limit},
        )

    def get_business_history(business_id: str, as_of_month: str) -> Dict[str, Any]:
        """Retrieve recent point-in-time business history."""
        return _execute(
            security_context,
            "get_business_history",
            {"business_id": business_id, "as_of_month": as_of_month},
        )

    def score_cashflow_risk(business_id: str, as_of_month: str) -> Dict[str, Any]:
        """Retrieve deterministic cash-flow risk scoring output."""
        return _execute(
            security_context,
            "score_cashflow_risk",
            {"business_id": business_id, "as_of_month": as_of_month},
        )

    def compare_with_peers(business_id: str, as_of_month: str) -> Dict[str, Any]:
        """Compare a business with its peer benchmark group."""
        return _execute(
            security_context,
            "compare_with_peers",
            {"business_id": business_id, "as_of_month": as_of_month},
        )

    def simulate_cashflow_scenario(
        business_id: str,
        as_of_month: str,
        inflow_change_pct: float,
        outflow_change_pct: float,
        collection_delay_change_days: float,
    ) -> Dict[str, Any]:
        """Run a deterministic cash-flow scenario simulation."""
        return _execute(
            security_context,
            "simulate_cashflow_scenario",
            {
                "business_id": business_id,
                "as_of_month": as_of_month,
                "inflow_change_pct": inflow_change_pct,
                "outflow_change_pct": outflow_change_pct,
                "collection_delay_change_days": collection_delay_change_days,
            },
        )

    def draft_intervention_plan(business_id: str, as_of_month: str) -> Dict[str, Any]:
        """Draft a non-executed intervention recommendation."""
        return _execute(
            security_context,
            "draft_intervention_plan",
            {"business_id": business_id, "as_of_month": as_of_month},
        )

    tools = [
        check_business_data_quality,
        get_portfolio_snapshot,
        get_business_history,
        score_cashflow_risk,
        compare_with_peers,
        simulate_cashflow_scenario,
        draft_intervention_plan,
    ]
    _assert_model_safe_tool_signatures(tools)
    return tools


def _assert_model_safe_tool_signatures(tools: Iterable[Callable[..., Any]]) -> None:
    forbidden = {
        "role",
        "user_id",
        "permissions",
        "security_context",
        "approved",
        "approval_status",
        "reviewer_id",
    }
    for tool in tools:
        params = set(inspect.signature(tool).parameters)
        if params & forbidden:
            raise ValueError(f"Model-safe tool '{tool.__name__}' exposes trusted fields.")
