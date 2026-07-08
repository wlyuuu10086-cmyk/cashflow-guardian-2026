import os
import pytest
from pathlib import Path
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk
from cashflow_guardian.data_engine.connection import get_database_path, get_readonly_connection

def test_risk_scoring_real_db():
    # End-to-end test on real database case
    res = score_cashflow_risk("B00001", "2025-06")
    
    assert res["business_id"] == "B00001"
    assert res["month"] == "2025-06"
    assert 0.0 <= res["risk_score"] <= 1.0
    assert res["risk_tier"] in ["RED", "AMBER", "GREEN", "CRITICAL"]
    assert res["scoring_mode"] in ["ml_model", "rule_based_fallback"]
    assert isinstance(res["warnings"], list)
    
def test_risk_scoring_refusal_invalid_business():
    with pytest.raises(ValueError) as exc:
        score_cashflow_risk("B99999", "2025-06")
    assert "was not found" in str(exc.value)

def test_risk_scoring_refusal_out_of_bounds_month():
    with pytest.raises(ValueError) as exc:
        score_cashflow_risk("B00001", "2026-01")
    assert "out of bounds" in str(exc.value)

def test_risk_scoring_refusal_insufficient_history():
    # B00001 has history starting 2024-01. Checking on 2024-02 has only 2 months of history
    with pytest.raises(ValueError) as exc:
        score_cashflow_risk("B00001", "2024-02")
    assert "Insufficient history" in str(exc.value)
