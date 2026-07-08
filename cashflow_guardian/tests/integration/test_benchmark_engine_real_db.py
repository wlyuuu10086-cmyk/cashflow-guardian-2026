import pytest
from cashflow_guardian.benchmark_engine.comparison import compare_business_with_peers

def test_benchmark_engine_real_db():
    # End-to-end integration test on real DuckDB database
    res = compare_business_with_peers("B00001", "2025-06")
    
    assert res.business_id == "B00001"
    assert res.as_of_month == "2025-06"
    assert res.peer_group.peer_count >= 0
    assert len(res.metrics) == 8
    
    # Check that core metrics have comparisons
    for metric_name in ["volatility", "collection_days", "late_invoice_rate", "repayment_burden", "payroll_burden", "credit_utilization", "overdraft_days", "trend"]:
        assert metric_name in res.metrics
        comp = res.metrics[metric_name]
        assert comp.direction in ["better", "similar", "worse", "unavailable"]
        assert comp.source_provenance in ["observed_data", "benchmark_table"]
        assert not res.provenance.future_data_used
