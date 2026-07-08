import pytest
from cashflow_guardian.tools.business import get_business_history_tool
from cashflow_guardian.tools.risk import score_cashflow_risk_tool
from cashflow_guardian.tools.benchmark import compare_with_peers_tool
from cashflow_guardian.tools.scenario import simulate_cashflow_scenario_tool
from cashflow_guardian.tools.intervention import draft_intervention_plan_tool
from cashflow_guardian.tools.portfolio import get_portfolio_snapshot_tool

def test_workflow_business_investigation():
    """1. Business Investigation Workflow:
    business history -> risk score -> peer benchmark -> intervention draft
    """
    bid = "B00001"
    month = "2025-06"
    
    # History
    hist = get_business_history_tool(bid, month, months=3)
    assert hist["status"] == "success"
    
    # Risk Score
    risk = score_cashflow_risk_tool(bid, month)
    assert risk["status"] == "success"
    
    # Benchmark
    bench = compare_with_peers_tool(bid, month)
    assert bench["status"] == "success"
    
    # Intervention Draft
    plan = draft_intervention_plan_tool(bid, month)
    assert plan["status"] == "success"
    assert plan["risk_tier"] == risk["risk_tier"]

def test_workflow_scenario_to_intervention():
    """2. Scenario Workflow:
    business history -> baseline risk -> downside simulation -> revised intervention draft
    """
    bid = "B00001"
    month = "2025-06"
    
    # Downside simulation
    sim = simulate_cashflow_scenario_tool(
        business_id=bid,
        as_of_month=month,
        inflow_change_pct=-20.0,
        collection_delay_change_days=15.0
    )
    assert sim["status"] == "success"
    
    # Revised intervention draft including the scenario outcome
    plan_scen = draft_intervention_plan_tool(
        business_id=bid,
        as_of_month=month,
        include_scenario=True,
        scenario_parameters={"inflow_change_pct": -20.0, "collection_delay_change_days": 15.0}
    )
    assert plan_scen["status"] == "success"
    assert any("short-term liquidity support" in act["action"] for act in plan_scen["recommended_draft_actions"])

def test_workflow_portfolio_scan():
    """3. Portfolio Workflow:
    portfolio snapshot -> bounded risk enrichment -> structured output
    """
    month = "2025-06"
    
    snapshot = get_portfolio_snapshot_tool(month, limit=10)
    assert snapshot["status"] == "success"
    assert len(snapshot["records"]) <= 10
    
    for rec in snapshot["records"]:
        assert "risk_score" in rec
        assert "risk_tier" in rec
        assert "principal_evidence" in rec
