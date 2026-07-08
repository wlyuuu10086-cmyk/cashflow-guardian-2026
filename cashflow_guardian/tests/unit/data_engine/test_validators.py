import pytest
from cashflow_guardian.data_engine.validators import (
    validate_business_id, validate_as_of_month, validate_history_length,
    ValidationError, InvalidBusinessIDError, BusinessIDNotFoundError,
    InvalidMonthError, OutOfBoundaryMonthError, InvalidHistoryLengthError
)

def test_validate_business_id_valid(mock_db_conn):
    """Tests validation of correct and existing business IDs."""
    assert validate_business_id("B00001", mock_db_conn) == "B00001"
    # Also support BUS_001 if mock database contains it (or format checks allow it)
    # Our regex allows BUS_001
    with pytest.raises(BusinessIDNotFoundError):
        validate_business_id("BUS_001", mock_db_conn)  # Format is valid, but it doesn't exist in mock_db_conn

def test_validate_business_id_invalid_format(mock_db_conn):
    """Tests validation of malformed business IDs."""
    with pytest.raises(InvalidBusinessIDError):
        validate_business_id("B123", mock_db_conn)
        
    with pytest.raises(InvalidBusinessIDError):
        validate_business_id("invalid_id", mock_db_conn)

def test_validate_business_id_not_found(mock_db_conn):
    """Tests validation of formatted but non-existent business IDs."""
    with pytest.raises(BusinessIDNotFoundError):
        validate_business_id("B99999", mock_db_conn)

def test_validate_business_id_sql_injection(mock_db_conn):
    """Tests that SQL injection characters in ID are rejected."""
    with pytest.raises(ValidationError):
        validate_business_id("B00001; DROP TABLE business_customers;", mock_db_conn)
        
    with pytest.raises(ValidationError):
        validate_business_id("B00001' OR '1'='1", mock_db_conn)

def test_validate_as_of_month_valid(mock_db_conn):
    """Tests validation of correct and available months."""
    assert validate_as_of_month("2025-03", mock_db_conn) == "2025-03"

def test_validate_as_of_month_malformed(mock_db_conn):
    """Tests validation of malformed month values."""
    with pytest.raises(InvalidMonthError):
        validate_as_of_month("2025/03", mock_db_conn)
        
    with pytest.raises(InvalidMonthError):
        validate_as_of_month("2025-13", mock_db_conn)

def test_validate_as_of_month_out_of_bounds(mock_db_conn):
    """Tests validation of month values outside of database available dates."""
    with pytest.raises(OutOfBoundaryMonthError):
        validate_as_of_month("2023-12", mock_db_conn)
        
    with pytest.raises(OutOfBoundaryMonthError):
        validate_as_of_month("2026-01", mock_db_conn)

def test_validate_history_length_valid():
    """Tests validation of history lengths within normal bounds."""
    assert validate_history_length(6) == 6
    assert validate_history_length(1) == 1
    assert validate_history_length(24) == 24

def test_validate_history_length_invalid():
    """Tests validation of invalid history lengths."""
    with pytest.raises(InvalidHistoryLengthError):
        validate_history_length(0)
        
    with pytest.raises(InvalidHistoryLengthError):
        validate_history_length(-5)
        
    with pytest.raises(InvalidHistoryLengthError):
        validate_history_length(25)
        
    with pytest.raises(InvalidHistoryLengthError):
        validate_history_length("6")  # Type error
