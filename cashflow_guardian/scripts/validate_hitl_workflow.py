import sys
import os
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cashflow_guardian.data_engine.connection import get_readonly_connection, get_database_path, check_database_health
from cashflow_guardian.tools.risk import score_cashflow_risk_tool
from cashflow_guardian.tools.benchmark import compare_with_peers_tool
from cashflow_guardian.tools.intervention import draft_intervention_plan_tool
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.watchlist import (
    create_watchlist_proposal,
    review_watchlist_proposal,
    get_active_watchlist,
    get_watchlist_action_history
)

def run_validation():
    print("========================================")
    print("VALIDATING HUMAN-IN-THE-LOOP WORKFLOW")
    print("========================================\n")

    # 1. Capture database metadata before running tests
    db_path = get_database_path()
    stat_before = os.stat(db_path)
    size_before = stat_before.st_size
    health_before = check_database_health()
    counts_before = dict(health_before.row_counts)

    print(f"Initial Database Size: {size_before} bytes")
    print(f"Initial Table Row Counts: {counts_before}\n")

    # 2. Select a valid business and month from snapshots
    conn = get_readonly_connection()
    row = conn.execute("SELECT business_id FROM business_customers LIMIT 1").fetchone()
    if not row:
        print("Error: No businesses found in database.")
        sys.exit(1)
    business_id = row[0]
    
    month_row = conn.execute("SELECT MAX(month) FROM business_monthly_snapshots WHERE business_id = ?", (business_id,)).fetchone()
    as_of_month = month_row[0] if month_row and month_row[0] else "2025-06"
    conn.close()

    print(f"Selected Business ID: {business_id}")
    print(f"Selected Month: {as_of_month}\n")

    # 3. Retrieve risk, benchmark, and intervention recommendation details
    print("--- Step 1: Querying Risk Score, Peer Benchmark, and Intervention Playbook ---")
    risk_result = score_cashflow_risk_tool(business_id, as_of_month)
    bench_result = compare_with_peers_tool(business_id, as_of_month)
    intervention_plan = draft_intervention_plan_tool(business_id, as_of_month)

    print(f"Risk Tier: {risk_result.get('risk_tier')}, Score: {risk_result.get('risk_score')}")
    print(f"Benchmark Peer Status: {bench_result.get('status')}")
    print(f"Intervention Recommend Playbook: '{intervention_plan.get('recommended_playbook')}'\n")

    # 4. Create proposal
    print("--- Step 2: Proposing watchlist addition (initiated by Relationship Manager) ---")
    ctx_propose = SecurityContext(
        request_id="req_val_hitl_propose",
        session_id="ses_123",
        user_id="RM_John",
        role="relationship_manager",
        requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z",
        source="dashboard",
        environment="demo"
    )

    prop = create_watchlist_proposal(
        business_id=business_id,
        as_of_month=as_of_month,
        proposed_by="RM_John",
        risk_result=risk_result,
        intervention_plan=intervention_plan,
        security_context=ctx_propose,
        idempotency_key=f"val_hitl_idem_{business_id}_{as_of_month}"
    )

    proposal_id = prop["proposal_id"]
    print(f"Watchlist Proposal Created: ID={proposal_id}, Status={prop['status']}\n")

    # 5. Attempt self-approval (proposer RM_John tries to approve)
    print("--- Step 3: Attempting self-approval by proposer (RM_John) ---")
    ctx_self = SecurityContext(
        request_id="req_val_hitl_self",
        session_id="ses_123",
        user_id="RM_John",
        role="risk_manager",
        requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z",
        source="dashboard",
        environment="demo"
    )

    try:
        review_watchlist_proposal(
            proposal_id=proposal_id,
            decision="approve",
            reviewed_by="RM_John",
            rationale="Approved by myself.",
            security_context=ctx_self
        )
        print("Violation: Allowed self-approval!")
        sys.exit(1)
    except Exception as e:
        print(f"Self-approval Blocked Successfully! Error: {e}\n")

    # 6. Approve with a different risk manager
    print("--- Step 4: Approving proposal by a different Risk Manager (Mgr_Sarah) ---")
    ctx_approve = SecurityContext(
        request_id="req_val_hitl_approve",
        session_id="ses_123",
        user_id="Mgr_Sarah",
        role="risk_manager",
        requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z",
        source="dashboard",
        environment="demo"
    )

    review_res = review_watchlist_proposal(
        proposal_id=proposal_id,
        decision="approve",
        reviewed_by="Mgr_Sarah",
        rationale=f"Risk score {risk_result.get('risk_score')} is high, and overdraft history is verified.",
        security_context=ctx_approve
    )

    print(f"Review Action Completed: Status={review_res['updated_status']}")
    print(f"Active Watchlist: {get_active_watchlist()}\n")

    # 7. Verify source DuckDB remains completely unchanged
    print("--- Step 5: Verifying source DuckDB database immutability ---")
    stat_after = os.stat(db_path)
    size_after = stat_after.st_size
    health_after = check_database_health()
    counts_after = dict(health_after.row_counts)

    print(f"Final Database Size: {size_after} bytes (Delta: {size_after - size_before})")
    print(f"Final Table Row Counts: {counts_after}")

    assert size_before == size_after, "Error: Source database file size changed!"
    assert counts_before == counts_after, "Error: Source database table counts changed!"
    print("Immutability Verified: 100% Unchanged!\n")
    print("Workflow Validation Completed Successfully!")

if __name__ == "__main__":
    run_validation()
