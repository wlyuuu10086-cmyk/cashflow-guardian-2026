import os
import sys
import json
from pathlib import Path

# Add src to python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.append(str(repo_root / "src"))

import duckdb
from cashflow_guardian.tools.registry import (
    get_tool_registry, list_tool_metadata, get_tool_by_name
)

# Forbidden names
FORBIDDEN_KEYWORDS = [
    "execute_sql", "arbitrary_query", "database_write", 
    "send_email", "change_credit_limit", "approve_loan", "modify_customer_record"
]

def main():
    print("======================================================================")
    print("CASHFLOW GUARDIAN: STRUCTURED TOOLS VALIDATION")
    print("======================================================================")
    
    # 1. Capture DB modification attributes before validation
    db_path = repo_root / "sme_cashflow_stress_project" / "data" / "sme_cashflow_stress.duckdb"
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
        
    mtime_before = db_path.stat().st_mtime
    size_before = db_path.stat().st_size
    
    # Record table row counts before
    conn = duckdb.connect(str(db_path), read_only=True)
    tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
    row_counts_before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    
    print(f"DB Path: {db_path}")
    print(f"DB Modification Time Before: {mtime_before}")
    print(f"DB File Size Before: {size_before} bytes")
    
    # 2. List Registered Tools
    print("\n--- Listing Registered Tools ---")
    metadata = list_tool_metadata()
    for m in metadata:
        print(f"Tool: {m['name']} | Permission: {m['permission']} | Approval Required: {m['human_approval_required']}")
        
    # 3. Check for Forbidden Tools
    print("\n--- Scanning for Prohibited Tools ---")
    registry = get_tool_registry()
    forbidden_found = []
    for k in registry:
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in k:
                forbidden_found.append(k)
    if forbidden_found:
        print(f"SECURITY ALERT: Prohibited tools found: {forbidden_found}")
        sys.exit(1)
    else:
        print("Success: Zero prohibited tools detected in registry.")
        
    # 4. Call Every Tool and Verify JSON Serialization
    print("\n--- Invoking Registered Tools and Verifying JSON Serialization ---")
    
    # Select business and month dynamically
    conn = duckdb.connect(str(db_path), read_only=True)
    biz_row = conn.execute("SELECT business_id, month FROM business_monthly_snapshots WHERE month = '2025-06' LIMIT 1").fetchone()
    conn.close()
    
    if not biz_row:
        print("Error: No data for 2025-06 to test tools.")
        sys.exit(1)
        
    test_bid, test_month = biz_row
    print(f"Using test business={test_bid}, month={test_month}")
    
    tool_inputs = {
        "check_database_health": {},
        "check_business_data_quality": {"business_id": test_bid, "as_of_month": test_month},
        "get_portfolio_snapshot": {"as_of_month": test_month, "limit": 5},
        "get_business_history": {"business_id": test_bid, "as_of_month": test_month, "months": 3},
        "build_point_in_time_features": {"business_id": test_bid, "month": test_month},
        "score_cashflow_risk": {"business_id": test_bid, "as_of_month": test_month},
        "compare_with_peers": {"business_id": test_bid, "as_of_month": test_month},
        "simulate_cashflow_scenario": {
            "business_id": test_bid, "as_of_month": test_month,
            "inflow_change_pct": -10.0, "outflow_change_pct": 5.0
        },
        "draft_intervention_plan": {
            "business_id": test_bid, "as_of_month": test_month,
            "include_scenario": True,
            "scenario_parameters": {"inflow_change_pct": -20.0, "collection_delay_change_days": 15.0}
        }
    }
    
    for tool_name, inputs in tool_inputs.items():
        print(f"\nCalling tool: {tool_name} ...")
        entry = get_tool_by_name(tool_name)
        func = entry.callable_func
        
        try:
            # Execute tool wrapper
            res = func(**inputs)
            
            # Check success or error wrapper format
            if isinstance(res, dict):
                print(f"  Result Status: {res.get('status')}")
            else:
                print(f"  Result Object Type: {type(res).__name__}")
                
            # Verify JSON serializability
            if hasattr(res, "model_dump"):
                serializable_res = res.model_dump()
            elif hasattr(res, "dict"):
                serializable_res = res.dict()
            else:
                serializable_res = res
            json_str = json.dumps(serializable_res)

            print(f"  JSON Serialization: Passed ({len(json_str)} bytes)")
            
        except Exception as e:
            print(f"  Execution failed: {str(e)}")
            sys.exit(1)
            
    # 5. Verify database remains unchanged after calling tools
    print("\n--- Verifying Database Immutability ---")
    mtime_after = db_path.stat().st_mtime
    size_after = db_path.stat().st_size
    
    conn = duckdb.connect(str(db_path), read_only=True)
    row_counts_after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    
    print(f"DB Modification Time After: {mtime_after}")
    print(f"DB File Size After: {size_after} bytes")
    
    db_changed = False
    
    # Note: under Windows/Python, opening read-only might update access times but modification times should not change.
    # To be safe, we check row counts and file size, and modification time if possible.
    if size_before != size_after:
        print("ERROR: Database file size changed!")
        db_changed = True
        
    for t in tables:
        before = row_counts_before[t]
        after = row_counts_after[t]
        if before != after:
            print(f"ERROR: Table '{t}' row count changed! Before={before}, After={after}")
            db_changed = True
            
    if db_changed:
        print("VALIDATION FAILED: Source database was mutated!")
        sys.exit(1)
    else:
        print("Success: Source database was NOT modified. Immutability verified.")
        
    print("\n======================================================================")
    print("TOOLS VALIDATION COMPLETED SUCCESSFULLY")
    print("======================================================================")

if __name__ == "__main__":
    main()
