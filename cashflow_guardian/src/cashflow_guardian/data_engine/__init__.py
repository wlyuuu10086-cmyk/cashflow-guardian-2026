"""Data Engine subpackage for CashFlow Guardian.

This package handles database connections, data quality audits, validation, metrics, 
and historical/portfolio features retrieval.
"""

from .connection import (
    get_database_path,
    get_readonly_connection,
    check_database_health,
    QuerySafetyError,
    DatabaseWriteError,
    validate_query_safety,
    validate_no_write
)

from .validators import (
    validate_business_id,
    validate_as_of_month,
    validate_history_length,
    ValidationError,
    InvalidBusinessIDError,
    BusinessIDNotFoundError,
    InvalidMonthError,
    OutOfBoundaryMonthError,
    InvalidHistoryLengthError
)

from .quality import check_business_data_quality

from .repository import (
    get_business_history,
    get_portfolio_snapshot,
    get_peer_benchmark
)

from .features import build_point_in_time_features

__all__ = [
    "get_database_path",
    "get_readonly_connection",
    "check_database_health",
    "QuerySafetyError",
    "DatabaseWriteError",
    "validate_query_safety",
    "validate_no_write",
    
    "validate_business_id",
    "validate_as_of_month",
    "validate_history_length",
    "ValidationError",
    "InvalidBusinessIDError",
    "BusinessIDNotFoundError",
    "InvalidMonthError",
    "OutOfBoundaryMonthError",
    "InvalidHistoryLengthError",
    
    "check_business_data_quality",
    
    "get_business_history",
    "get_portfolio_snapshot",
    "get_peer_benchmark",
    
    "build_point_in_time_features"
]
