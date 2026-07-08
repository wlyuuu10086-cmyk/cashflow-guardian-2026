import pytest
from unittest.mock import patch
from cashflow_guardian.data_engine.features import build_point_in_time_features

def test_build_point_in_time_features(mock_db_conn):
    """Tests building point-in-time feature vectors and verifying correctness."""
    with patch("cashflow_guardian.data_engine.features.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn):
         
        fv = build_point_in_time_features("B00001", "2025-06")
        
        assert fv.business_id == "B00001"
        assert fv.month == "2025-06"
        assert fv.future_data_used is False
        assert fv.provenance.future_data_used is False
        
        # Verify feature names match dictionary keys
        assert len(fv.features) > 0
        assert set(fv.feature_names) == set(fv.features.keys())
        
        # Verify 3-month rolling mean cash inflow calculation
        # Snaps for B00001 cash inflow observed are all 10000.0, so mean is 10000.0
        assert fv.features["cash_inflow_3m_avg"] == 10000.0
        assert fv.features["cash_outflow_3m_avg"] == 8000.0
        assert fv.features["net_cash_flow_3m_avg"] == 2000.0
        
        # Verify overdraft days sum
        assert fv.features["overdraft_days_3m_sum"] == 0
        
        # Verify industry benchmark gap features
        assert "industry_margin_gap" in fv.features
        assert "industry_volatility_ratio" in fv.features
        assert "industry_collection_days_gap" in fv.features
        
        # Verify consecutive negative cash flow months (current is 2000.0 > 0, so streak = 0)
        assert fv.features["consecutive_negative_cash_flow_months"] == 0

def test_build_features_insufficient_history(mock_db_conn):
    """Tests that building features for business with insufficient history returns failure features."""
    with patch("cashflow_guardian.data_engine.features.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.repository.get_readonly_connection", return_value=mock_db_conn):
         
        # B00002 has only 2 months of history as of 2025-06
        fv = build_point_in_time_features("B00002", "2025-06")
        
        # Failure behavior: empty features, list warnings
        assert fv.features == {}
        assert fv.feature_names == []
        assert len(fv.missing_feature_warnings) > 0
        assert any("Insufficient history" in w for w in fv.missing_feature_warnings)
