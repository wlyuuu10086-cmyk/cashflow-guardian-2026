import pytest
from unittest.mock import patch
import duckdb

from cashflow_guardian.benchmark_engine.peer_groups import determine_peer_group
from cashflow_guardian.benchmark_engine.comparison import (
    compare_business_with_peers, calculate_percentile_rank, get_months_prior
)

def test_determine_peer_group_exclusion(mock_db_conn):
    """Tests that the target business is excluded from the peer group."""
    with patch("cashflow_guardian.benchmark_engine.peer_groups.determine_peer_group") as mock_peer:
        # Check B00001 is excluded in actual determination logic
        method, industry, revenue_band, peer_ids = determine_peer_group("B00001", "2025-06", mock_db_conn, min_peer_count=1)
        assert "B00001" not in peer_ids
        # Since B00001 is Wholesale Trade and B00002 is Retail Trade, B00002 is not in B00001's peer group.
        # But let's check that the output list does not contain B00001.
        assert len(peer_ids) == 0  # No other Wholesale Trade businesses in mock data

def test_peer_group_fallback_to_benchmark_table(mock_db_conn):
    """Tests fallback behavior when peer count is below threshold."""
    # Since only B00001 exists as Wholesale Trade and we exclude it, peer count is 0.
    # With min_peer_count=5, it must fallback to the industry_benchmark table.
    method, industry, revenue_band, peer_ids = determine_peer_group("B00001", "2025-06", mock_db_conn, min_peer_count=5)
    assert method == "industry_benchmark_table"
    assert len(peer_ids) == 0

def test_percentile_rank_calculation():
    """Tests the percentile rank formula and boundaries."""
    peers = [10.0, 20.0, 30.0, 40.0, 50.0]
    # Business value is 30.0 (3 peers: 10, 20, 30 are <= 30) => rank is 3/5 * 100 = 60.0%
    rank = calculate_percentile_rank(peers, 30.0)
    assert rank == 60.0
    
    # Check boundary cases
    assert calculate_percentile_rank([], 30.0) == 0.0
    assert calculate_percentile_rank(peers, 5.0) == 0.0
    assert calculate_percentile_rank(peers, 60.0) == 100.0

def test_unsupported_metrics_fallback(mock_db_conn):
    """Tests that fallback benchmarking returns 'unavailable' for metrics not in the benchmark table."""
    with patch("cashflow_guardian.benchmark_engine.comparison.de.get_readonly_connection", return_value=mock_db_conn):
        res = compare_business_with_peers("B00001", "2025-06", min_peer_count=5)
        assert res.peer_group.method == "industry_benchmark_table"
        
        # Check unsupported metrics
        late_inv = res.metrics["late_invoice_rate"]
        assert late_inv.direction == "unavailable"
        assert late_inv.interpretation_code == "METRIC_UNAVAILABLE"
        assert "Metric 'late_invoice_rate' comparison is unavailable" in res.warnings[0] or any("late_invoice_rate" in w for w in res.warnings)

def test_compare_business_with_peers_pit(mock_db_conn):
    """Tests that peer calculations do not use records newer than target month."""
    with patch("cashflow_guardian.benchmark_engine.comparison.de.get_readonly_connection", return_value=mock_db_conn):
        # B00001 as of 2025-04 should only see historical data <= 2025-04
        # We check this by running the comparison and ensuring provenance is safe
        res = compare_business_with_peers("B00001", "2025-04", min_peer_count=5)
        assert res.as_of_month == "2025-04"
        assert not res.provenance.future_data_used
        assert res.provenance.as_of_month == "2025-04"
