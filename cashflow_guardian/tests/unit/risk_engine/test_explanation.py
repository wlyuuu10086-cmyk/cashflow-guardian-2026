import pytest
from unittest.mock import patch, MagicMock
from cashflow_guardian.risk_engine.explanation import generate_explanation

def test_generate_explanation_structure():
    feature_vector = {
        "cash_inflow": 20000.0,
        "cash_outflow": 18000.0,
        "net_cash_flow": 2000.0,
        "ending_cash_balance": 50000.0,
        "avg_daily_balance": 48000.0,
        "overdraft_days": 1,
        "payroll_amount": 5000.0,
        "scheduled_debt_service": 2000.0,
        "max_dpd": 0,
        "consecutive_negative_cash_flow_months": 0,
        "industry_margin_gap": -0.05,
        "industry_collection_days_gap": 5.0,
        "industry_volatility_ratio": 1.2
    }
    
    explanation = generate_explanation(
        business_id="B00001",
        month="2025-06",
        risk_score=0.15,
        risk_tier="GREEN",
        feature_vector=feature_vector,
        model_type="random_forest"
    )
    
    assert explanation.business_id == "B00001"
    assert explanation.month == "2025-06"
    assert explanation.observed_facts["ending_cash_balance"] == 50000.0
    assert explanation.deterministic_metrics["margin"] == pytest.approx(0.1) # 2000 / 20000
    assert explanation.model_predictions["assigned_risk_tier"] == "GREEN"
    assert len(explanation.interpretations) > 0
    assert any("Disclaimer" in d for d in explanation.interpretations)
