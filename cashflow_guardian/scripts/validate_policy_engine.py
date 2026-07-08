import sys
import os
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.engine import evaluate_tool_request

def run_validation():
    print("========================================")
    print("VALIDATING POLICY ENGINE AND RBAC RULES")
    print("========================================\n")

    # Setup a valid security context for relationship manager
    ctx_rm = SecurityContext(
        request_id="req_val_policy_ok",
        session_id="ses_123",
        user_id="RM_01",
        role="relationship_manager",
        requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z",
        source="dashboard",
        environment="demo"
    )

    # 1. Approved Read Request
    print("--- Scenario 1: Approved portfolio read request by Relationship Manager ---")
    decision1 = evaluate_tool_request(ctx_rm, "get_portfolio_snapshot", {"month": "2025-06"})
    print(f"Allowed: {decision1.allowed}")
    print(f"Policy Codes: {decision1.policy_codes}")
    print(f"Warnings: {decision1.warnings}")
    print("Success!\n")

    # 2. Denied Request (Administrator attempting to read portfolio)
    print("--- Scenario 2: Denied portfolio read request by Administrator ---")
    ctx_admin = SecurityContext(
        request_id="req_val_policy_deny",
        session_id="ses_123",
        user_id="Admin_01",
        role="administrator",
        requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z",
        source="dashboard",
        environment="demo"
    )
    decision2 = evaluate_tool_request(ctx_admin, "get_portfolio_snapshot", {"month": "2025-06"})
    print(f"Allowed: {decision2.allowed}")
    print(f"Policy Codes: {decision2.policy_codes}")
    print(f"Warnings: {decision2.warnings}")
    print("Success!\n")

    # 3. Unknown Tool Denial
    print("--- Scenario 3: Unknown tool request ---")
    decision3 = evaluate_tool_request(ctx_rm, "unknown_tool_xyz", {"arg": "val"})
    print(f"Allowed: {decision3.allowed}")
    print(f"Policy Codes: {decision3.policy_codes}")
    print(f"Warnings: {decision3.warnings}")
    print("Success!\n")

    # 4. Forbidden Action Denial (Arbitrary SQL / Database write attempts)
    print("--- Scenario 4: Forbidden database write argument ---")
    decision4 = evaluate_tool_request(ctx_rm, "get_business_history", {
        "business_id": "BUS_001",
        "month": "2025-06",
        "sql": "DROP TABLE repayments"
    })
    print(f"Allowed: {decision4.allowed}")
    print(f"Policy Codes: {decision4.policy_codes}")
    print(f"Warnings: {decision4.warnings}")
    print("Success!\n")

if __name__ == "__main__":
    run_validation()
