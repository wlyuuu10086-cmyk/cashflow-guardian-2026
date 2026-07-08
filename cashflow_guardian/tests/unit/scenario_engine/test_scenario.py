import pytest
from unittest.mock import patch
import cashflow_guardian.data_engine as de

from cashflow_guardian.scenario_engine.simulation import simulate_cashflow_scenario
from cashflow_guardian.scenario_engine.assumptions import validate_assumptions

@pytest.fixture
def patch_db(mock_db_conn):
    """Fixture to redirect all DB queries across the codebase to mock_db_conn."""
    with patch("cashflow_guardian.data_engine.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.features.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.benchmark_engine.comparison.de.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.risk_engine.scoring.de.get_readonly_connection", return_value=mock_db_conn):
        yield

def test_validate_assumptions_invalid():
    """Tests out of bounds assumptions are rejected."""
    with pytest.raises(ValueError) as exc:
        validate_assumptions(inflow_change_pct=-150.0, outflow_change_pct=0.0, collection_delay_change_days=0.0, payroll_change_pct=0.0, debt_service_change_pct=0.0)
    assert "Inflow change pct" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        validate_assumptions(inflow_change_pct=0.0, outflow_change_pct=0.0, collection_delay_change_days=200.0, payroll_change_pct=0.0, debt_service_change_pct=0.0)
    assert "Collection delay change days" in str(exc.value)

def test_no_change_scenario_matches_baseline(patch_db, mock_db_conn):
    """Tests that a no-change scenario produces the exact same results as baseline."""
    res = simulate_cashflow_scenario(
        business_id="B00001",
        as_of_month="2025-06",
        inflow_change_pct=0.0,
        outflow_change_pct=0.0,
        collection_delay_change_days=0.0,
        payroll_change_pct=0.0,
        debt_service_change_pct=0.0
    )
    
    # Verify baseline equals simulated for raw metrics
    assert res.simulated.cash_inflow == pytest.approx(res.baseline.cash_inflow)
    assert res.simulated.cash_outflow == pytest.approx(res.baseline.cash_outflow)
    assert res.simulated.net_cash_flow == pytest.approx(res.baseline.net_cash_flow)
    assert res.simulated.payroll_amount == pytest.approx(res.baseline.payroll_amount)
    assert res.simulated.debt_service == pytest.approx(res.baseline.debt_service)
    assert res.simulated.collection_days == pytest.approx(res.baseline.collection_days)
    assert res.simulated.repayment_burden_ratio == pytest.approx(res.baseline.repayment_burden_ratio)
    assert res.simulated.payroll_burden_ratio == pytest.approx(res.baseline.payroll_burden_ratio)
    assert res.simulated.liquidity_gap == pytest.approx(res.baseline.liquidity_gap)
    
    # Verify risk score matches within a tight tolerance (e.g. 1e-5)
    assert res.simulated.risk_score == pytest.approx(res.baseline.risk_score, abs=1e-5)
    assert res.simulated.risk_tier == res.baseline.risk_tier
    assert res.risk_tier_change == "no_change"

def test_collection_delay_cash_impact(patch_db, mock_db_conn):
    """Tests collection delay formula and deferred cash impact."""
    # Let's run with 15 days delay (which is half a month, i.e., 50% of invoice amount deferred)
    res = simulate_cashflow_scenario(
        business_id="B00001",
        as_of_month="2025-06",
        collection_delay_change_days=15.0
    )
    
    details = res.collection_delay_details
    assert details is not None
    assert "amount_of_inflow_deferred" in details
    
    # B00001 has mock snapshot invoice_amount_total = 5000.0. 
    # 15 days delay => 15/30 = 0.50 => 2500.0 deferred
    assert details["amount_of_inflow_deferred"] == pytest.approx(2500.0)
    
    # Simulated inflow should be baseline inflow (10000.0) minus deferred (2500.0) = 7500.0
    assert res.simulated.cash_inflow == pytest.approx(7500.0)

def test_baseline_inputs_not_mutated(patch_db, mock_db_conn):
    """Verifies that running the simulation does not mutate baseline data structures."""
    # Fetch baseline features once
    fv_before = de.build_point_in_time_features("B00001", "2025-06")
    inflow_before = fv_before.features["cash_inflow"]
    
    # Simulate downside
    res = simulate_cashflow_scenario(
        business_id="B00001",
        as_of_month="2025-06",
        inflow_change_pct=-50.0
    )
    
    # Verify baseline value in result matches what we fetched before
    assert res.baseline.cash_inflow == inflow_before
    
    # Fetch again to verify no side-effects in cache/connection
    fv_after = de.build_point_in_time_features("B00001", "2025-06")
    assert fv_after.features["cash_inflow"] == inflow_before
