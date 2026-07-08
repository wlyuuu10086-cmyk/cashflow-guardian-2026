import pytest
from unittest.mock import patch
from cashflow_guardian.data_engine.quality import check_business_data_quality

def test_data_quality_valid_complete(mock_db_conn):
    """Tests data quality check for a valid complete business case."""
    with patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.validators.get_db_month_range", return_value=("2025-01", "2025-12")):
        # B00001 has 6 months of data, ending in 2025-06
        dq = check_business_data_quality("B00001", "2025-06")
        
        assert dq.status == "COMPLETED"
        assert dq.can_build_features is True
        assert len(dq.missing_fields) == 0
        assert len(dq.missing_months) == 0
        assert dq.transaction_gaps is False
        assert dq.has_sufficient_history is True
        assert len(dq.errors) == 0
        assert dq.provenance is not None
        assert dq.provenance.future_data_used is False

def test_data_quality_insufficient_history(mock_db_conn):
    """Tests data quality check for a business with less than 3 months of snapshots."""
    with patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.validators.get_db_month_range", return_value=("2025-01", "2025-12")):
        # B00002 has only 2 months of data (2025-05, 2025-06)
        dq = check_business_data_quality("B00002", "2025-06")
        
        assert dq.status == "WARNING"
        # Lacking history must block feature construction (predictive scoring needs 3 months)
        assert dq.can_build_features is False
        assert dq.has_sufficient_history is False
        assert any("Insufficient history" in w for w in dq.warnings)

def test_data_quality_missing_target_month(mock_db_conn):
    """Tests data quality check when target month snapshot is missing."""
    with patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.validators.get_db_month_range", return_value=("2025-01", "2025-12")):
        # Month 2025-04 is missing for B00002 in mock_db_conn
        dq = check_business_data_quality("B00002", "2025-04")
        
        assert dq.status == "BLOCKED"
        assert dq.can_build_features is False
        assert any("Missing snapshot for target month" in e for e in dq.errors)

def test_data_quality_missing_required_fields(mock_db_conn):
    """Tests that missing required financial fields blocks feature construction."""
    # Insert a row for a new business with NULL required fields
    mock_db_conn.execute(
        "INSERT INTO business_customers (business_id, business_name) VALUES ('B00003', 'Null Corp')"
    )
    mock_db_conn.execute(
        """
        INSERT INTO business_monthly_snapshots (
            business_id, month, opening_cash_balance_proxy, ending_cash_balance_proxy, 
            cash_inflow_observed, cash_outflow_observed, transaction_count
        ) VALUES
        ('B00003', '2025-01', 10000.0, 10000.0, 1000.0, 1000.0, 10),
        ('B00003', '2025-02', 10000.0, 10000.0, 1000.0, 1000.0, 10),
        ('B00003', '2025-03', NULL, 10000.0, 1000.0, 1000.0, 10)
        """
    )
    
    with patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.validators.get_db_month_range", return_value=("2025-01", "2025-12")):
        dq = check_business_data_quality("B00003", "2025-03")
        
        assert dq.status == "BLOCKED"
        assert dq.can_build_features is False
        assert "opening_cash_balance_proxy" in dq.missing_fields
        assert any("Missing required financial field" in e for e in dq.errors)

def test_data_quality_optional_fields_absent(mock_db_conn):
    """Tests that absence of optional data (invoice/payroll/repayment) does NOT block features."""
    # Insert a row with NULL optional data but correct required fields
    mock_db_conn.execute(
        "INSERT INTO business_customers (business_id, business_name) VALUES ('B00004', 'No Activity Corp')"
    )
    # Insert 3 months so history check passes
    for m in ["2025-01", "2025-02"]:
        mock_db_conn.execute(
            """
            INSERT INTO business_monthly_snapshots (
                business_id, month, opening_cash_balance_proxy, ending_cash_balance_proxy, 
                cash_inflow_observed, cash_outflow_observed, transaction_count
            ) VALUES
            ('B00004', ?, 5000.0, 5000.0, 1000.0, 1000.0, 10)
            """,
            (m,)
        )
    mock_db_conn.execute(
        """
        INSERT INTO business_monthly_snapshots (
            business_id, month, opening_cash_balance_proxy, ending_cash_balance_proxy, 
            cash_inflow_observed, cash_outflow_observed, transaction_count,
            invoice_amount_total, payroll_amount, scheduled_debt_service
        ) VALUES
        ('B00004', '2025-03', 5000.0, 5000.0, 1000.0, 1000.0, 10, NULL, NULL, NULL)
        """
    )
    
    with patch("cashflow_guardian.data_engine.quality.get_readonly_connection", return_value=mock_db_conn), \
         patch("cashflow_guardian.data_engine.validators.get_db_month_range", return_value=("2025-01", "2025-12")):
        dq = check_business_data_quality("B00004", "2025-03")
        
        # It should not block feature construction because optional fields are allowed to be NULL/absent
        assert dq.can_build_features is True
        assert dq.status == "COMPLETED"
        assert len(dq.errors) == 0
        assert any("Optional invoicing data is absent" in w for w in dq.warnings)
        assert any("Optional payroll data is absent" in w for w in dq.warnings)
        assert any("Optional loan/repayment data is absent" in w for w in dq.warnings)
