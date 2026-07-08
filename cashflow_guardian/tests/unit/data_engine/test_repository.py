import pytest
from unittest.mock import patch
from cashflow_guardian.data_engine.repository import (
    get_business_history, get_portfolio_snapshot, get_peer_benchmark
)

def test_get_business_history(mock_db_conn):
    """Tests fetching business history up to target month."""
    with patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn):
        history = get_business_history("B00001", "2025-04", months=3)
        
        assert history.business_id == "B00001"
        assert history.history_months == 3
        # Should contain months 2025-02, 2025-03, 2025-04 (chronological order)
        assert [snap.month for snap in history.snapshots] == ["2025-02", "2025-03", "2025-04"]
        
        # Test lookahead bounding: month 2025-05 and 2025-06 must NOT be in the result
        for snap in history.snapshots:
            assert snap.month <= "2025-04"

def test_get_business_history_insufficient(mock_db_conn):
    """Tests fetching history when fewer months are available than requested."""
    with patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn):
        # Request 6 months for B00002 which only has 2 months
        history = get_business_history("B00002", "2025-06", months=6)
        
        assert history.history_months == 2
        assert len(history.snapshots) == 2
        assert len(history.provenance.warnings) > 0
        assert "only 2 months were available" in history.provenance.warnings[0]

def test_get_portfolio_snapshot(mock_db_conn):
    """Tests fetching portfolio snapshot for a specific month."""
    with patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn):
        snapshot = get_portfolio_snapshot("2025-06")
        
        assert snapshot.as_of_month == "2025-06"
        # B00001 and B00002 both have data for 2025-06
        assert len(snapshot.records) == 2
        
        biz_ids = {r.business_id for r in snapshot.records}
        assert biz_ids == {"B00001", "B00002"}
        
        # Check that we can filter by industry
        snap_filtered = get_portfolio_snapshot("2025-06", industry="Wholesale Trade")
        assert len(snap_filtered.records) == 1
        assert snap_filtered.records[0].business_id == "B00001"

def test_get_peer_benchmark(mock_db_conn):
    """Tests fetching peer benchmarks and observed deviations."""
    with patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn):
        benchmark = get_peer_benchmark("B00001", "2025-06")
        
        assert benchmark.business_id == "B00001"
        assert benchmark.industry == "Wholesale Trade"
        
        # Peer metrics check
        assert benchmark.peer_metrics["benchmark_margin"] == 0.15
        assert benchmark.peer_metrics["benchmark_cash_flow_volatility"] == 0.20
        assert benchmark.peer_metrics["benchmark_collection_days"] == 12.0
        
        # Observed values
        # B00001 has net cash flow = 2000.0, inflow = 10000.0 => margin = 2000/10000 = 0.20
        assert benchmark.business_metrics["current_margin"] == 0.20
        assert benchmark.business_metrics["avg_collection_days"] == 10.0
        
        # Deviations: current_margin - benchmark_margin = 0.20 - 0.15 = 0.05
        assert benchmark.deviations["margin_delta"] == pytest.approx(0.05)
        # collection_days_delta: 10 - 12 = -2.0
        assert benchmark.deviations["collection_days_delta"] == pytest.approx(-2.0)
