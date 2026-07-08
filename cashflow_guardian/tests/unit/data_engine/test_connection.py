import pytest
import os
import duckdb
from pathlib import Path
from cashflow_guardian.data_engine.connection import (
    get_database_path, get_readonly_connection, check_database_health,
    validate_query_safety, validate_no_write, QuerySafetyError, DatabaseWriteError
)

def test_database_path_resolves():
    """Tests that the database path resolves to a valid path containing the duckdb file."""
    path = get_database_path()
    assert isinstance(path, Path)
    assert path.name == "sme_cashflow_stress.duckdb"
    assert path.exists()

def test_source_database_opens_read_only():
    """Tests that the connection is opened in read-only mode and write operations fail."""
    conn = get_readonly_connection()
    try:
        # Check that we can read
        res = conn.execute("SELECT COUNT(*) FROM business_customers").fetchone()
        assert res[0] > 0
        
        # Check that writing fails
        with pytest.raises((duckdb.InvalidInputException, PermissionError, duckdb.Error)):
            conn.execute("CREATE TABLE test_connection_write (a INT)")
            
    finally:
        conn.close()

def test_database_health_check():
    """Tests the database health check against the real database."""
    health = check_database_health()
    assert health.database_available is True
    assert health.read_only is True
    assert health.required_tables_present is True
    assert len(health.missing_tables) == 0
    assert len(health.row_counts) > 0
    assert health.database_size_bytes > 0

def test_query_safety_validation():
    """Tests that SQL queries containing lookahead tables or fields are blocked."""
    # Safe query
    validate_query_safety("SELECT * FROM business_monthly_snapshots WHERE month = '2025-06'")
    
    # Prohibited tables
    with pytest.raises(QuerySafetyError):
        validate_query_safety("SELECT * FROM business_monthly_outcomes")
        
    # Prohibited columns
    with pytest.raises(QuerySafetyError):
        validate_query_safety("SELECT future_60d_cash_stress_observed FROM snapshots")

def test_no_write_validation():
    """Tests that SQL queries containing write commands are blocked by safety guard."""
    # Safe select query
    validate_no_write("SELECT * FROM business_customers")
    
    # Blocked write verbs
    with pytest.raises(DatabaseWriteError):
        validate_no_write("INSERT INTO business_customers (business_id) VALUES ('B99999')")
        
    with pytest.raises(DatabaseWriteError):
        validate_no_write("CREATE TABLE temp_table (a INT)")
        
    with pytest.raises(DatabaseWriteError):
        validate_no_write("DROP TABLE business_customers")
