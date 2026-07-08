import pytest
from cashflow_guardian.scenario_engine.simulation import simulate_cashflow_scenario

def test_scenario_engine_real_db():
    # End-to-end integration test on real DuckDB database
    # B00001 as of 2025-06
    res = simulate_cashflow_scenario(
        business_id="B00001",
        as_of_month="2025-06",
        inflow_change_pct=-20.0,
        outflow_change_pct=10.0,
        collection_delay_change_days=15.0
    )
    
    assert res.business_id == "B00001"
    assert res.as_of_month == "2025-06"
    assert res.assumptions["inflow_change_pct"] == -20.0
    
    # Inflow should drop (baseline: ~15k-25k)
    assert res.simulated.cash_inflow < res.baseline.cash_inflow
    
    # Net cash flow should drop
    assert res.simulated.net_cash_flow < res.baseline.net_cash_flow
    
    # Verify risk score outputs
    assert 0.0 <= res.baseline.risk_score <= 1.0
    assert 0.0 <= res.simulated.risk_score <= 1.0
    assert res.risk_tier_change in ["deteriorated", "improved", "no_change"]
    assert not res.future_data_used
