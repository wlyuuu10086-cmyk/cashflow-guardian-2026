import re
import duckdb
from typing import List, Tuple

class ValidationError(ValueError):
    """Base class for all input validation errors."""
    pass

class InvalidBusinessIDError(ValidationError):
    """Raised when business ID does not match expected naming format."""
    pass

class BusinessIDNotFoundError(ValidationError):
    """Raised when business ID is not found in the database."""
    pass

class InvalidMonthError(ValidationError):
    """Raised when as-of month does not match YYYY-MM format."""
    pass

class OutOfBoundaryMonthError(ValidationError):
    """Raised when as-of month is outside dynamically verified bounds."""
    pass

class InvalidHistoryLengthError(ValidationError):
    """Raised when history length is not a valid number of months."""
    pass

def validate_business_id(business_id: str, conn: duckdb.DuckDBPyConnection) -> str:
    """Validates the business ID.
    Authoritative check is existence in business_customers.
    Also validates that the input has no SQL injection patterns and follows a pattern.
    """
    if not business_id:
        raise ValidationError("Business ID cannot be empty or null.")
    
    # Sanitization and basic format check (supporting real B00001 and spec BUS_001)
    if not re.match(r"^(B\d{5}|BUS_\d{3,4})$", business_id):
        raise InvalidBusinessIDError(f"Business ID format is invalid: '{business_id}'")
    
    # Security: check for SQL injection patterns in input
    if ";" in business_id or "--" in business_id or "/*" in business_id:
        raise ValidationError("SQL injection characters detected in business ID.")

    # Authoritative check: existence in database
    cursor = conn.execute("SELECT COUNT(*) FROM business_customers WHERE business_id = ?", (business_id,))
    exists = cursor.fetchone()[0] > 0
    if not exists:
        raise BusinessIDNotFoundError(f"Business ID '{business_id}' was not found in the database.")
    
    return business_id

def get_db_month_range(conn: duckdb.DuckDBPyConnection) -> Tuple[str, str]:
    """Queries the minimum and maximum available months in business_monthly_snapshots."""
    row = conn.execute("SELECT MIN(month), MAX(month) FROM business_monthly_snapshots").fetchone()
    if not row or not row[0] or not row[1]:
        # Return fallback boundaries if snapshots are empty
        return "2024-01", "2025-12"
    return row[0], row[1]

def validate_as_of_month(as_of_month: str, conn: duckdb.DuckDBPyConnection) -> str:
    """Validates the as-of month against YYYY-MM format and dynamic database boundaries."""
    if not as_of_month:
        raise ValidationError("As-of month cannot be empty or null.")
        
    if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", as_of_month):
        raise InvalidMonthError(f"As-of month format is invalid: '{as_of_month}'. Must be YYYY-MM.")
    
    # Query database to get available month range
    min_month, max_month = get_db_month_range(conn)
    
    # Simple string comparison works for YYYY-MM format
    if as_of_month < min_month or as_of_month > max_month:
        raise OutOfBoundaryMonthError(
            f"Requested month '{as_of_month}' is out of bounds. "
            f"Available range is {min_month} to {max_month}."
        )
    
    return as_of_month

def validate_history_length(months: int) -> int:
    """Validates that history length is a positive integer within bounds."""
    if not isinstance(months, int) or isinstance(months, bool):
         raise InvalidHistoryLengthError("History length must be a valid integer.")
    if months <= 0:
        raise InvalidHistoryLengthError("History length must be positive.")
    if months > 24:
        raise InvalidHistoryLengthError("History length cannot exceed 24 months.")
    return months
