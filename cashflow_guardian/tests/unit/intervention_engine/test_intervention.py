import pytest
from unittest.mock import MagicMock

from cashflow_guardian.intervention_engine.recommendations import draft_intervention_plan
from cashflow_guardian.intervention_engine.rules import PROHIBITED_ACTIONS

def test_intervention_low_risk():
    """Tests low-risk GREEN tier recommendations."""
    risk_res = {"risk_tier": "GREEN", "risk_score": 0.05, "warnings": []}
    
    # Mock benchmark result
    bench_res = MagicMock()
    bench_res.metrics = {}
    
    plan = draft_intervention_plan("B00001", "2025-06", risk_res, bench_res)
    assert plan.risk_tier == "GREEN"
    assert plan.priority == "low"
    assert len(plan.recommended_draft_actions) == 1
    assert plan.recommended_draft_actions[0].action == "continue routine monitoring"
    assert not plan.human_approval_required
    
    # Verify prohibited actions are listed but blocked
    assert len(plan.prohibited_actions) == len(PROHIBITED_ACTIONS)
    for act in plan.recommended_draft_actions:
        assert act.action not in PROHIBITED_ACTIONS

def test_intervention_high_risk_watchlist():
    """Tests high-risk RED tier watchlist proposal requires approval."""
    risk_res = {"risk_tier": "RED", "risk_score": 0.85, "warnings": []}
    
    bench_res = MagicMock()
    bench_res.metrics = {}
    
    plan = draft_intervention_plan("B00001", "2025-06", risk_res, bench_res)
    assert plan.risk_tier == "RED"
    assert plan.priority == "high"
    
    actions = [act.action for act in plan.recommended_draft_actions]
    assert "contact relationship manager for manual review" in actions
    assert "propose demonstration watchlist review" in actions
    assert plan.human_approval_required

def test_intervention_high_repayment_burden():
    """Tests repayment burden trigger causes repayment schedule review."""
    risk_res = {"risk_tier": "GREEN", "risk_score": 0.12, "warnings": []}
    
    # Repayment burden exceeds 25% warning threshold
    repay_comp = MagicMock()
    repay_comp.business_value = 0.35
    
    bench_res = MagicMock()
    bench_res.metrics = {"repayment_burden": repay_comp}
    
    plan = draft_intervention_plan("B00001", "2025-06", risk_res, bench_res)
    actions = [act.action for act in plan.recommended_draft_actions]
    assert "review repayment schedule" in actions
    assert plan.priority == "medium"  # Upgraded from low

def test_intervention_collection_delay_gap():
    """Tests collection delay gap trigger causes receivables verification."""
    risk_res = {"risk_tier": "GREEN", "risk_score": 0.10, "warnings": []}
    
    coll_comp = MagicMock()
    coll_comp.business_value = 55.0
    coll_comp.peer_value = 30.0
    coll_comp.absolute_gap = 25.0
    
    bench_res = MagicMock()
    bench_res.metrics = {"collection_days": coll_comp}
    
    plan = draft_intervention_plan("B00001", "2025-06", risk_res, bench_res)
    actions = [act.action for act in plan.recommended_draft_actions]
    assert "verify large outstanding invoices" in actions
    assert plan.priority == "medium"
