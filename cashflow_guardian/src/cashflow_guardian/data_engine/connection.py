import os
import re
import yaml
import duckdb
from pathlib import Path
from typing import Dict, List, Any
from .schemas import DatabaseHealthResult

class QuerySafetyError(ValueError):
    """Raised when an inference query attempts to access forbidden tables or columns."""
    pass

class DatabaseWriteError(PermissionError):
    """Raised when a query attempts to perform database write operations."""
    pass

def get_repo_root() -> Path:
    """Resolves the repository root dynamically."""
    # File is at: cashflow_guardian/src/cashflow_guardian/data_engine/connection.py
    return Path(__file__).resolve().parent.parent.parent.parent

def get_database_path() -> Path:
    """Resolves the database path declared in config/database.yaml relative to repository root."""
    repo_root = get_repo_root()
    config_path = repo_root / "config" / "database.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Database configuration file not found at {config_path}")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    db_rel_path = config["database"]["path"]
    return repo_root / db_rel_path

def validate_query_safety(sql: str) -> None:
    """Enforces point-in-time leakage-prevention on the SQL statement.
    Blocks queries accessing outcomes table or future outcome columns.
    """
    sql_upper = sql.upper()
    if "BUSINESS_MONTHLY_OUTCOMES" in sql_upper:
        raise QuerySafetyError("Inference query safety violation: Access to 'business_monthly_outcomes' table is prohibited.")
    
    # Check for future outcome columns
    if "FUTURE_60D_" in sql_upper:
        raise QuerySafetyError("Inference query safety violation: Access to future outcome columns starting with 'future_60d_' is prohibited.")

def validate_no_write(sql: str) -> None:
    """Validates that no write operation is attempted in the SQL statement."""
    sql_upper = sql.upper()
    # Simple check for write keywords as full words to prevent false positives on fields like created_at
    write_verbs = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]
    for verb in write_verbs:
        if re.search(r"\b" + verb + r"\b", sql_upper):
            raise DatabaseWriteError(f"Database write operation blocked: SQL contains prohibited '{verb}' instruction.")

def get_readonly_connection() -> duckdb.DuckDBPyConnection:
    """Returns a read-only DuckDB connection."""
    db_path = get_database_path()
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB database file not found at {db_path}")
    
    try:
        # Enforce read-only connection
        conn = duckdb.connect(str(db_path), read_only=True)
        return conn
    except Exception as e:
        raise ConnectionError(f"Failed to open connection to DuckDB: {e}")

def check_database_health() -> DatabaseHealthResult:
    """Checks the health and read-only status of the database."""
    warnings: List[str] = []
    missing_tables: List[str] = []
    row_counts: Dict[str, int] = {}
    db_size = 0
    read_only_verified = False
    db_available = False
    
    repo_root = get_repo_root()
    db_path = get_database_path()
    
    # Check file existence
    if not db_path.exists():
        warnings.append(f"Database file does not exist at {db_path}")
        return DatabaseHealthResult(
            database_available=False,
            read_only=False,
            required_tables_present=False,
            missing_tables=[],
            row_counts={},
            warnings=warnings,
            database_size_bytes=0
        )
    
    db_size = db_path.stat().st_size
    
    # Load expected tables from config
    config_path = repo_root / "config" / "database.yaml"
    expected_tables = []
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            expected_tables = config.get("schemas", {}).get("expected_tables", [])
    
    conn = None
    try:
        conn = get_readonly_connection()
        db_available = True
        
        # Verify read-only enforcement by catching DuckDB error or verifying via system catalogs
        try:
            conn.execute("CREATE TABLE test_health (a INT)")
            # If this succeeded, then it is NOT read-only
            warnings.append("Security violation: Database connection allowed writing.")
            # Clean up if it somehow wrote (should not happen with read_only=True)
            conn.execute("DROP TABLE test_health")
        except duckdb.InvalidInputException:
            read_only_verified = True
        except Exception:
            # Any other exception means write failed, which is expected
            read_only_verified = True
        
        # Get actual tables in DB
        db_tables_raw = conn.execute("SHOW TABLES").fetchall()
        db_tables = {row[0].lower() for row in db_tables_raw}
        
        # Check expected tables presence and fetch row counts
        for tbl in expected_tables:
            tbl_lower = tbl.lower()
            if tbl_lower in db_tables:
                count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                row_counts[tbl] = count
            else:
                missing_tables.append(tbl)
        
        required_tables_present = (len(missing_tables) == 0)
        if not required_tables_present:
            warnings.append(f"Missing expected tables: {', '.join(missing_tables)}")
            
    except Exception as e:
        warnings.append(f"Database connection error: {e}")
        required_tables_present = False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return DatabaseHealthResult(
        database_available=db_available,
        read_only=read_only_verified,
        required_tables_present=required_tables_present,
        missing_tables=missing_tables,
        row_counts=row_counts,
        warnings=warnings,
        database_size_bytes=db_size
    )
