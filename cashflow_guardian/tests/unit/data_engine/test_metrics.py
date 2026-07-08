import pytest
from cashflow_guardian.data_engine.metrics import (
    net_cash_flow, repayment_burden_ratio, payroll_burden_ratio,
    cash_flow_volatility, percentage_change, rolling_mean,
    consecutive_negative_cash_flow_months, benchmark_absolute_gap,
    benchmark_percentage_gap
)

def test_net_cash_flow():
    assert net_cash_flow(10000.0, 8000.0) == 2000.0
    assert net_cash_flow(None, 5000.0) == -5000.0
    assert net_cash_flow(8000.0, None) == 8000.0
    assert net_cash_flow(None, None) == 0.0

def test_repayment_burden_ratio():
    assert repayment_burden_ratio(2500.0, 10000.0) == 0.25
    assert repayment_burden_ratio(None, 10000.0) is None
    assert repayment_burden_ratio(2500.0, None) is None
    assert repayment_burden_ratio(2500.0, 0.0) is None

def test_payroll_burden_ratio():
    assert payroll_burden_ratio(3000.0, 10000.0) == 0.30
    assert payroll_burden_ratio(None, 10000.0) is None
    assert payroll_burden_ratio(3000.0, 0.0) is None

def test_cash_flow_volatility():
    # Normal values
    assert cash_flow_volatility([100.0, 200.0, 300.0]) == pytest.approx(100.0)
    # Fewer than 2 observations
    assert cash_flow_volatility([100.0]) is None
    assert cash_flow_volatility([None, 100.0]) is None
    # Filters out None values
    assert cash_flow_volatility([100.0, None, 200.0, 300.0]) == pytest.approx(100.0)

def test_percentage_change():
    # Formula: (current_value - previous_value) / abs(previous_value)
    assert percentage_change(120.0, 100.0) == 0.20
    assert percentage_change(80.0, 100.0) == -0.20
    assert percentage_change(10.0, -10.0) == 2.0  # (10 - (-10)) / 10 = 2.0
    # Zero denominator
    assert percentage_change(100.0, 0.0) is None
    # Null values
    assert percentage_change(None, 100.0) is None
    assert percentage_change(100.0, None) is None

def test_rolling_mean():
    assert rolling_mean([10.0, 20.0, 30.0]) == 20.0
    assert rolling_mean([10.0, None, 30.0]) == 20.0
    assert rolling_mean([]) is None
    assert rolling_mean([None]) is None

def test_consecutive_negative_cash_flow_months():
    # Streak starts from the end and goes backwards
    assert consecutive_negative_cash_flow_months([-100.0, -200.0, 300.0, -400.0]) == 1
    assert consecutive_negative_cash_flow_months([-100.0, -200.0, -300.0]) == 3
    assert consecutive_negative_cash_flow_months([100.0, 200.0]) == 0
    assert consecutive_negative_cash_flow_months([-100.0, None, -200.0]) == 1  # None stops streak
    assert consecutive_negative_cash_flow_months([]) == 0

def test_benchmark_absolute_gap():
    assert benchmark_absolute_gap(0.12, 0.15) == pytest.approx(-0.03)
    assert benchmark_absolute_gap(None, 0.15) is None

def test_benchmark_percentage_gap():
    assert benchmark_percentage_gap(20, 10) == 1.0  # (20 - 10) / 10 = 1.0
    assert benchmark_percentage_gap(10, 0) is None
    assert benchmark_percentage_gap(None, 10) is None
