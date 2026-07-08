import pytest
from unittest.mock import patch, MagicMock

from cashflow_guardian.tools.registry import (
    get_tool_registry, list_tool_metadata, get_tool_by_name
)
from cashflow_guardian.agent.tool_adapter import (
    MODEL_SAFE_TOOL_NAMES,
    get_model_safe_tool_specs,
)
from cashflow_guardian.tools.portfolio import get_portfolio_snapshot_tool
from cashflow_guardian.tools.business import get_business_history_tool, check_business_data_quality_tool
from cashflow_guardian.tools.risk import score_cashflow_risk_tool
from cashflow_guardian.tools.benchmark import compare_with_peers_tool
from cashflow_guardian.tools.scenario import simulate_cashflow_scenario_tool

# Forbidden keywords
FORBIDDEN_KEYWORDS = [
    "execute_sql", "arbitrary_query", "database_write", 
    "send_email", "change_credit_limit", "approve_loan", "modify_customer_record"
]

def test_registry_has_no_forbidden_tools():
    """Checks that no forbidden tools are registered."""
    registry = get_tool_registry()
    for name in registry:
        for keyword in FORBIDDEN_KEYWORDS:
            assert keyword not in name, f"Prohibited tool name found: {name}"

def test_tool_failure_returns_safe_structured_error():
    """Tests that tool wrappers catch exceptions and return safe, structured errors."""
    with patch("cashflow_guardian.tools.business.de.repository.get_business_history", side_effect=ValueError("Invalid business format B123")):
        res = get_business_history_tool("B123", "2025-06")
        assert res["status"] == "error"
        assert res["error_code"] == "INVALID_ARGUMENTS"
        assert "Invalid business format" in res["message"]
        assert "B123" in res["message"]
        # Ensure no tracebacks or path leakage
        assert "traceback" not in str(res).lower()
        assert "C:\\" not in str(res)
        assert "d:/" not in str(res)

def test_tool_db_failure_returns_retryable_error():
    """Tests that DB failures return safe retryable errors."""
    with patch("cashflow_guardian.tools.business.de.repository.get_business_history", side_effect=ConnectionError("DuckDB file locked")):
        res = get_business_history_tool("B00001", "2025-06")
        assert res["status"] == "error"
        assert res["error_code"] == "DATABASE_ERROR"
        assert res["retryable"] is True
        # Ensure raw DB connection info is not exposed
        assert "DuckDB file locked" not in res["message"]

def test_registry_metadata_contracts():
    """Verifies internal registry contents match approved application tools."""
    metadata = list_tool_metadata()
    names = {m["name"] for m in metadata}
    expected_names = {
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
        "approve_or_reject_watchlist_action",
    }
    assert names == expected_names

    for item in metadata:
        assert item["permission"] in {"read-only", "write"}
        assert isinstance(item["human_approval_required"], bool)
        assert isinstance(item["allowed_source_tables"], list)
        assert isinstance(item["prohibited_behaviors"], list)


def test_model_safe_tool_allowlist_is_separate_from_internal_registry():
    """Model-visible tools are a safe subset of the complete internal registry."""
    internal_names = set(get_tool_registry())
    model_names = set(MODEL_SAFE_TOOL_NAMES)

    assert model_names < internal_names
    assert "approve_or_reject_watchlist_action" not in model_names
    assert "propose_watchlist_action" not in model_names

    for name in model_names:
        entry = get_tool_by_name(name)
        assert entry.permission == "read-only"
        assert entry.human_approval_required is False


def test_model_safe_tool_specs_do_not_accept_trusted_identity_fields():
    """No model-exposed tool can construct or override authorization context."""
    forbidden_params = {
        "role",
        "user_id",
        "permissions",
        "approval_status",
        "approved",
        "security_context",
        "reviewer_id",
    }

    for spec in get_model_safe_tool_specs():
        assert set(spec["parameters"]).isdisjoint(forbidden_params)
