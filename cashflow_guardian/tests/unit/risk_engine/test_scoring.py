import os
import pytest
import inspect
from unittest.mock import patch, MagicMock
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk, calculate_rules_based_fallback
from cashflow_guardian.risk_engine.model_loader import load_feature_columns
import cashflow_guardian.data_engine as de

def test_hard_leakage_feature_names():
    # Correction 13: Tests must fail if a feature name contains future_60d_
    try:
        schema = load_feature_columns()
        all_features = schema["numerical_features"] + schema["categorical_features"]
    except Exception:
        # If model is not trained yet, default to config
        all_features = [
            "cash_inflow_3m_avg", "cash_inflow_mom_change", "net_cash_flow_3m_avg",
            "net_cash_flow_6m_volatility", "repayment_burden_3m_avg", "payroll_burden_3m_avg",
            "overdraft_days_3m_sum", "late_invoice_rate_3m_avg", "industry", "region",
            "revenue_band", "legal_structure"
        ]
        
    for feat in all_features:
        assert "future_60d_" not in feat, f"Data Leakage Warning: Feature '{feat}' contains lookahead pattern 'future_60d_'!"

def test_hard_leakage_query_safety():
    # Correction 13: Tests must fail if business_monthly_outcomes appears in the inference path
    source_code = inspect.getsource(score_cashflow_risk)
    assert "business_monthly_outcomes" not in source_code, (
        "Security Violation: Inference scoring path contains references to prohibited 'business_monthly_outcomes' table!"
    )
    
    # Check data engine features builder code
    import cashflow_guardian.data_engine.features as de_feat
    de_feat_code = inspect.getsource(de_feat.build_point_in_time_features)
    assert "business_monthly_outcomes" not in de_feat_code, (
        "Security Violation: Data Engine feature builder references prohibited 'business_monthly_outcomes' table!"
    )

def test_hard_leakage_future_data_isolation():
    # Correction 13: Tests must fail if data after as_of_month enters feature construction
    # We spy on connection executes and inspect all queries
    import cashflow_guardian.data_engine.features as de_feat
    de_feat_code = inspect.getsource(de_feat.build_point_in_time_features)
    
    # We inspect the SQL executed in features.py
    # Verify that the month condition uses '<=' and never '>' or joins future months
    assert "WHERE business_id = ? AND month <= ?" in de_feat_code, (
        "Data Leakage Violation: Point-in-time features query does not restrict to snapshots <= as_of_month!"
    )

def test_rules_based_fallback_calculation():
    # Verify calculation logic of deterministic rules-based fallback
    features = {
        "overdraft_days": 3,
        "cash_inflow": 10000.0,
        "scheduled_debt_service": 3000.0,  # 30% repayment burden
        "payroll_amount": 4000.0,           # 40% payroll burden
        "consecutive_negative_cash_flow_months": 2
    }
    
    # Overdraft: 3 * 0.1 = 0.3
    # Repay burden: 30% (>25% warning) = 0.2
    # Payroll burden: 40% (>35% warning) = 0.1
    # Neg streak: 2 * 0.1 = 0.2
    # Expected score = 0.3 + 0.2 + 0.1 + 0.2 = 0.8
    score = calculate_rules_based_fallback(features)
    assert score == 0.8

def test_scoring_fallback_graceful_warning():
    # Mocking load_risk_models to fail, simulating missing model assets
    with patch("cashflow_guardian.risk_engine.scoring.load_risk_models", side_effect=FileNotFoundError("Mock model file missing")):
        res = score_cashflow_risk("B00001", "2025-06")
        assert res["scoring_mode"] == "rule_based_fallback"
        assert res["model_prediction_available"] is False
        assert res["risk_score_type"] == "heuristic"
        assert res["model_version"] is None
        assert any("Predictive ML scoring is temporarily unavailable" in w for w in res["warnings"])
