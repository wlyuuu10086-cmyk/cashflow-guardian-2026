"""Structured Agent Tools subpackage."""

from .portfolio import get_portfolio_snapshot_tool
from .business import get_business_history_tool, check_business_data_quality_tool
from .risk import score_cashflow_risk_tool
from .benchmark import compare_with_peers_tool
from .scenario import simulate_cashflow_scenario_tool
from .intervention import draft_intervention_plan_tool

from .registry import (
    get_tool_registry,
    get_tool_by_name,
    list_tool_metadata,
    ToolRegistryEntry,
    execute_tool_with_policy,
    ToolExecutionResult
)

__all__ = [
    "get_portfolio_snapshot_tool",
    "get_business_history_tool",
    "check_business_data_quality_tool",
    "score_cashflow_risk_tool",
    "compare_with_peers_tool",
    "simulate_cashflow_scenario_tool",
    "draft_intervention_plan_tool",
    "get_tool_registry",
    "get_tool_by_name",
    "list_tool_metadata",
    "ToolRegistryEntry",
    "execute_tool_with_policy",
    "ToolExecutionResult"
]
