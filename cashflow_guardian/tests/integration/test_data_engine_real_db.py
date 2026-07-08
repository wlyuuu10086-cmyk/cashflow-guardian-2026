import os
import pytest
import duckdb
from pathlib import Path
from cashflow_guardian.data_engine.connection import (
    get_database_path, get_readonly_connection, QuerySafetyError, DatabaseWriteError,
    validate_query_safety, validate_no_write
)
from cashflow_guardian.data_engine.validators import validate_business_id, ValidationError
import cashflow_guardian.data_engine as de

def get_table_counts(conn) -> dict:
    """Helper to fetch row counts of all expected tables."""
    tables = [
        "business_customers", "bank_transactions", "invoices", "loans", 
        "repayments", "payroll", "business_monthly_snapshots", "industry_benchmark"
    ]
    counts = {}
    for table in tables:
        try:
            res = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = res[0]
        except Exception:
            counts[table] = -1
    return counts

def test_absence_of_arbitrary_sql_functions():
    """Asserts that no arbitrary SQL execution functions are exposed."""
    forbidden_names = ["execute_sql", "run_sql", "query_database", "arbitrary_query"]
    for name in forbidden_names:
        assert not hasattr(de, name), f"Security violation: found public function '{name}' in Data Engine."

def test_sql_injection_rejection():
    """Asserts that SQL-like business ID inputs are rejected."""
    conn = get_readonly_connection()
    try:
        injection_inputs = [
            "B00001; DROP TABLE business_customers;",
            "B00001' OR '1'='1",
            "B00001-- comment",
            "B00001/* comment */"
        ]
        for inj in injection_inputs:
            with pytest.raises(ValidationError):
                validate_business_id(inj, conn)
    finally:
        conn.close()

def test_rejection_of_source_table_writes():
    """Asserts that write operations against the DuckDB database fail."""
    conn = get_readonly_connection()
    try:
        # Check select works
        conn.execute("SELECT 1")
        
        # Test connection-level block on CREATE
        with pytest.raises((duckdb.InvalidInputException, PermissionError, duckdb.Error)):
            conn.execute("CREATE TABLE dummy_test (id INT)")
            
        # Test connection-level block on INSERT
        with pytest.raises((duckdb.InvalidInputException, PermissionError, duckdb.Error)):
            conn.execute("INSERT INTO business_customers (business_id) VALUES ('B99999')")
            
        # Test helper functions block write commands
        with pytest.raises(DatabaseWriteError):
            validate_no_write("INSERT INTO business_customers (business_id) VALUES ('B99999')")
            
        with pytest.raises(DatabaseWriteError):
            validate_no_write("DROP TABLE business_customers")
            
    finally:
        conn.close()

def test_rejection_of_outcomes_and_future_fields():
    """Asserts that queries referencing outcomes table or future outcome columns are blocked."""
    # Test outcomes table block
    with pytest.raises(QuerySafetyError):
        validate_query_safety("SELECT * FROM business_monthly_outcomes")
        
    # Test future_60d_* fields block
    with pytest.raises(QuerySafetyError):
        validate_query_safety("SELECT future_60d_cash_stress_observed FROM business_monthly_snapshots")
        
    with pytest.raises(QuerySafetyError):
        validate_query_safety("SELECT business_id, future_60d_dpd30_flag FROM snapshots")

def test_database_immutability():
    """Verifies that running the data engine does not modify database file or row counts."""
    db_path = get_database_path()
    
    # 1. Capture file modification timestamp and row counts BEFORE tests
    mtime_before = db_path.stat().st_mtime
    
    conn_before = get_readonly_connection()
    row_counts_before = get_table_counts(conn_before)
    conn_before.close()
    
    # 2. Run multiple data engine operations against real database
    health = de.check_database_health()
    assert health.database_available is True
    
    dq = de.check_business_data_quality("B00001", "2025-06")
    assert dq.can_build_features is True
    
    history = de.get_business_history("B00001", "2025-06", months=6)
    assert history.history_months == 6
    
    portfolio = de.get_portfolio_snapshot("2025-06", limit=10)
    assert len(portfolio.records) > 0
    
    peer = de.get_peer_benchmark("B00001", "2025-06")
    assert peer.industry is not None
    
    fv = de.build_point_in_time_features("B00001", "2025-06")
    assert fv.features["cash_inflow"] > 0.0
    
    # 3. Capture file modification timestamp and row counts AFTER tests
    mtime_after = db_path.stat().st_mtime
    
    conn_after = get_readonly_connection()
    row_counts_after = get_table_counts(conn_after)
    conn_after.close()
    
    # 4. Assert no change
    assert mtime_before == mtime_after, "Error: Database file modification timestamp changed!"
    assert row_counts_before == row_counts_after, "Error: Database table row counts changed!"
