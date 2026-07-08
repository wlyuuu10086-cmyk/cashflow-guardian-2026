import sys
import os
import time
from pathlib import Path

# Add src directory to path so we can import cashflow_guardian

import cashflow_guardian.data_engine as de

def get_table_counts(conn) -> dict:
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

def run_validation():
    print("==========================================================")
    print("      CASHFLOW GUARDIAN DATA ENGINE VALIDATION SCRIPT     ")
    print("==========================================================\n")
    
    db_path = de.get_database_path()
    print(f"Database Path: {db_path}")
    print(f"Database Size: {db_path.stat().st_size} bytes\n")
    
    # 1. Capture DB state BEFORE validation
    mtime_before = db_path.stat().st_mtime
    conn_check = de.get_readonly_connection()
    counts_before = get_table_counts(conn_check)
    conn_check.close()
    
    print("--- 1. Database Immutability Check (Pre-run) ---")
    print(f"File Modification Time: {mtime_before}")
    print(f"Source Table Counts: {counts_before}\n")
    
    # 2. Database Health Check
    print("--- 2. Database Health Check ---")
    health = de.check_database_health()
    print(f"Available: {health.database_available}")
    print(f"Read-Only: {health.read_only}")
    print(f"Required Tables Present: {health.required_tables_present}")
    print(f"Warnings: {health.warnings}\n")
    
    # 3. Data Quality Check
    print("--- 3. Business Data-Quality Check (Valid Case) ---")
    valid_id = "B00001"
    valid_month = "2025-06"
    dq = de.check_business_data_quality(valid_id, valid_month)
    print(f"Status: {dq.status}")
    print(f"Can build features: {dq.can_build_features}")
    print(f"Errors: {dq.errors}")
    print(f"Warnings: {dq.warnings}\n")
    
    # 4. Business History Retrieval
    print("--- 4. Business History Retrieval ---")
    history = de.get_business_history(valid_id, valid_month, months=6)
    print(f"Retrieved months: {history.history_months}")
    if history.snapshots:
        latest = history.snapshots[-1]
        print(f"Latest Month: {latest.month}")
        print(f"Cash Inflow: {latest.cash_inflow}")
        print(f"Ending Balance: {latest.ending_balance}")
    print(f"History Provenance: {history.provenance.model_dump()}\n")
    
    # 5. Portfolio Snapshot
    print("--- 5. Portfolio Snapshot ---")
    portfolio = de.get_portfolio_snapshot(valid_month, limit=5)
    print(f"Target Month: {portfolio.as_of_month}")
    print(f"Records returned: {len(portfolio.records)}")
    if portfolio.records:
        r = portfolio.records[0]
        print(f"Sample Record -> ID: {r.business_id}, Name: {r.business_name}, Risk Status: {r.data_quality_status}")
    print(f"Portfolio Provenance: {portfolio.provenance.model_dump()}\n")
    
    # 6. Peer Benchmark
    print("--- 6. Peer Benchmark ---")
    peer = de.get_peer_benchmark(valid_id, valid_month)
    print(f"Industry: {peer.industry}")
    print(f"Business Margin: {peer.business_metrics['current_margin']:.4f}")
    print(f"Benchmark Margin: {peer.peer_metrics['benchmark_margin']:.4f}")
    print(f"Margin Delta: {peer.deviations['margin_delta']:.4f}")
    print(f"Collection Days Delta: {peer.deviations['collection_days_delta']:.1f}")
    print(f"Benchmark Provenance: {peer.provenance.model_dump()}\n")
    
    # 7. Point-in-time Feature Construction
    print("--- 7. Point-in-time Feature Construction ---")
    fv = de.build_point_in_time_features(valid_id, valid_month)
    print(f"Feature Vector length: {len(fv.features)}")
    print(f"Feature Names: {fv.feature_names[:10]} ... (total {len(fv.feature_names)})")
    print(f"Future Data Used flag: {fv.future_data_used}")
    print(f"Feature Provenance future_data_used: {fv.provenance.future_data_used}")
    print(f"Feature Provenance table list: {fv.provenance.source_tables}\n")
    
    # 8. Invalid ID Handling
    print("--- 8. Invalid Business Handling ---")
    invalid_id = "B99999"
    try:
        de.get_business_history(invalid_id, valid_month)
    except Exception as e:
        print(f"Expected Error Caught: {type(e).__name__} - {e}\n")
        
    # 9. Boundary Month Handling
    print("--- 9. Boundary Month Handling (Latest Available Month) ---")
    boundary_month = "2025-12"
    dq_boundary = de.check_business_data_quality(valid_id, boundary_month)
    print(f"As of Month: {boundary_month}")
    print(f"Data Quality Status: {dq_boundary.status}")
    print(f"Can build features: {dq_boundary.can_build_features}")
    print(f"Errors: {dq_boundary.errors}")
    print(f"Warnings: {dq_boundary.warnings}\n")
    
    # 10. Attempted Source Write Rejection
    print("--- 10. Attempted Source Write Rejection ---")
    conn = None
    try:
        conn = de.get_readonly_connection()
        conn.execute("INSERT INTO business_customers (business_id) VALUES ('B99999')")
        print("ERROR: Write succeeded on read-only connection!")
    except Exception as e:
        print(f"Expected Connection Write Error caught: {type(e).__name__} - {e}")
        
    try:
        de.validate_no_write("INSERT INTO business_customers (business_id) VALUES ('B99999')")
    except Exception as e:
        print(f"Expected Safety Guard Write Error caught: {type(e).__name__} - {e}\n")
        
    if conn:
        conn.close()
        
    # 11. Capture DB state AFTER validation
    mtime_after = db_path.stat().st_mtime
    conn_check = de.get_readonly_connection()
    counts_after = get_table_counts(conn_check)
    conn_check.close()
    
    print("--- 11. Database Immutability Check (Post-run) ---")
    print(f"File Modification Time: {mtime_after}")
    print(f"Source Table Counts: {counts_after}\n")
    
    # Assert database is unchanged
    assert mtime_before == mtime_after, "FAIL: Database modification timestamp changed!"
    assert counts_before == counts_after, "FAIL: Database table counts changed!"
    print("SUCCESS: Source database is completely untouched and unmodified.")
    print("==========================================================")

if __name__ == "__main__":
    run_validation()
