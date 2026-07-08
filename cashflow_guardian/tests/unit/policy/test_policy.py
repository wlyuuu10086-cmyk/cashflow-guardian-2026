import pytest
import os
import json
import tempfile
import threading
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.permissions import has_permission, get_required_permission_for_tool
from cashflow_guardian.policy.engine import evaluate_tool_request
from cashflow_guardian.policy.approval import validate_state_transition, validate_approval_decision
from cashflow_guardian.policy.watchlist import (
    create_watchlist_proposal,
    review_watchlist_proposal,
    list_pending_watchlist_proposals,
    get_watchlist_action_history
)

@pytest.fixture
def temp_actions_file():
    """Provides a temporary file path for demo actions to ensure test isolation."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)  # Let the store initialize it
    old_env = os.environ.get("CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH")
    os.environ["CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH"] = path
    yield path
    # Clean up
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    if old_env is not None:
        os.environ["CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH"] = old_env
    else:
        os.environ.pop("CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH", None)

def test_role_permissions():
    # Analyst permissions
    assert has_permission("analyst", "portfolio.read")
    assert has_permission("analyst", "business.read")
    assert has_permission("analyst", "risk.read")
    assert has_permission("analyst", "benchmark.read")
    assert has_permission("analyst", "scenario.run")
    assert has_permission("analyst", "intervention.draft")
    assert has_permission("analyst", "watchlist.propose")
    assert not has_permission("analyst", "watchlist.approve")

    # Relationship Manager permissions
    assert has_permission("relationship_manager", "watchlist.propose")
    assert not has_permission("relationship_manager", "watchlist.approve")

    # Risk Manager permissions
    assert has_permission("risk_manager", "watchlist.approve")
    assert has_permission("risk_manager", "watchlist.reject")

    # System Agent permissions
    assert has_permission("system_agent", "portfolio.read")
    assert not has_permission("system_agent", "watchlist.approve")

    # Administrator permissions
    assert has_permission("administrator", "audit.read")
    assert not has_permission("administrator", "portfolio.read")

def test_policy_engine_rules():
    ctx_analyst = SecurityContext(
        request_id="req_1", session_id="ses_1", user_id="user_analyst",
        role="analyst", requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )

    # 1. Allowed request
    decision = evaluate_tool_request(ctx_analyst, "get_portfolio_snapshot", {"month": "2025-06"})
    assert decision.allowed
    assert decision.permission_granted
    assert "POLICY_TOOL_ALLOWED" in decision.policy_codes

    # 2. Denied tool due to missing permission
    ctx_admin = SecurityContext(
        request_id="req_2", session_id="ses_1", user_id="user_admin",
        role="administrator", requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )
    decision = evaluate_tool_request(ctx_admin, "get_portfolio_snapshot", {"month": "2025-06"})
    assert not decision.allowed
    assert "POLICY_PERMISSION_MISSING" in decision.policy_codes

    # 3. Forbidden tool name (database write or arbitrary SQL)
    decision = evaluate_tool_request(ctx_analyst, "execute_sql", {"sql": "SELECT * FROM business_customers"})
    assert not decision.allowed
    assert "POLICY_TOOL_DENIED" in decision.policy_codes

    # 4. Prohibited behavior (arbitrary SQL/database write arguments)
    decision = evaluate_tool_request(ctx_analyst, "get_business_history", {
        "business_id": "BUS_001",
        "month": "2025-06",
        "db_action": "DROP TABLE repayments;"
    })
    assert not decision.allowed
    assert "POLICY_DATABASE_WRITE_BLOCKED" in decision.policy_codes

    # 5. Accessing future outcomes
    decision = evaluate_tool_request(ctx_analyst, "get_business_history", {
        "business_id": "BUS_001",
        "month": "2025-06",
        "table_name": "BUSINESS_MONTHLY_OUTCOMES"
    })
    assert not decision.allowed
    assert "POLICY_FUTURE_DATA_BLOCKED" in decision.policy_codes

def test_watchlist_proposal_state_machine():
    # Valid transitions
    ok, _ = validate_state_transition("pending", "approved")
    assert ok
    ok, _ = validate_state_transition("pending", "rejected")
    assert ok
    ok, _ = validate_state_transition("pending", "expired")
    assert ok
    ok, _ = validate_state_transition("pending", "cancelled")
    assert ok

    # Invalid transitions
    ok, _ = validate_state_transition("approved", "pending")
    assert not ok
    ok, _ = validate_state_transition("approved", "rejected")
    assert not ok
    ok, _ = validate_state_transition("rejected", "approved")
    assert not ok
    ok, _ = validate_state_transition("expired", "approved")
    assert not ok
    ok, _ = validate_state_transition("cancelled", "approved")
    assert not ok

def test_watchlist_workflow_persistence(temp_actions_file):
    # Setup database check helpers
    risk_result = {
        "risk_score": 0.85,
        "risk_tier": "RED",
        "scoring_mode": "ml_model",
        "model_version": "RandomForest",
        "feature_contributions": [{"feature_name": "overdraft_days", "contribution_value": 0.3}],
        "provenance": {"future_data_used": False, "warnings": []}
    }
    
    intervention_plan = {
        "evidence_codes": ["DELINQUENCY_RISK"],
        "recommended_playbook": "Contact client RM",
        "allowed_actions": ["manual review"]
    }

    ctx_proposer = SecurityContext(
        request_id="req_propose", session_id="ses_1", user_id="user_rm",
        role="relationship_manager", requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )

    # 1. Propose addition
    prop = create_watchlist_proposal(
        business_id="BUS_001",
        as_of_month="2025-06",
        proposed_by="user_rm",
        risk_result=risk_result,
        intervention_plan=intervention_plan,
        security_context=ctx_proposer,
        idempotency_key="idem_key_1"
    )
    
    assert prop["status"] == "pending"
    assert prop["business_id"] == "BUS_001"
    assert prop["risk_score"] == 0.85
    assert prop["risk_tier"] == "RED"
    assert "DELINQUENCY_RISK" in prop["evidence_codes"]

    # 2. Idempotent proposal creation (returns existing proposal)
    prop_dup = create_watchlist_proposal(
        business_id="BUS_001",
        as_of_month="2025-06",
        proposed_by="user_rm",
        risk_result=risk_result,
        intervention_plan=intervention_plan,
        security_context=ctx_proposer,
        idempotency_key="idem_key_1"
    )
    assert prop_dup["proposal_id"] == prop["proposal_id"]

    # 3. List pending proposals
    ctx_approver = SecurityContext(
        request_id="req_review", session_id="ses_1", user_id="user_risk_mgr",
        role="risk_manager", requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )
    pending_list = list_pending_watchlist_proposals(ctx_approver)
    assert len(pending_list) == 1
    assert pending_list[0]["proposal_id"] == prop["proposal_id"]

    # 4. Proposer self-approval restriction
    ctx_self_approver = SecurityContext(
        request_id="req_self_review", session_id="ses_1", user_id="user_rm",
        role="risk_manager", requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )
    with pytest.raises(ValueError, match="Conflict of interest"):
        review_watchlist_proposal(
            proposal_id=prop["proposal_id"],
            decision="approve",
            reviewed_by="user_rm",
            rationale="Approved",
            security_context=ctx_self_approver
        )

    # 5. Non-risk manager cannot review
    ctx_analyst = SecurityContext(
        request_id="req_analyst_review", session_id="ses_1", user_id="user_analyst",
        role="analyst", requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )
    with pytest.raises(ValueError, match="not authorized to review"):
        review_watchlist_proposal(
            proposal_id=prop["proposal_id"],
            decision="approve",
            reviewed_by="user_analyst",
            rationale="Looks good",
            security_context=ctx_analyst
        )

    # 6. Valid approval by risk manager
    res = review_watchlist_proposal(
        proposal_id=prop["proposal_id"],
        decision="approve",
        reviewed_by="user_risk_mgr",
        rationale="Risks verified",
        security_context=ctx_approver
    )
    assert res["updated_status"] == "approved"

    # 7. Duplicate approval conflict
    with pytest.raises(ValueError, match="Conflict"):
        review_watchlist_proposal(
            proposal_id=prop["proposal_id"],
            decision="approve",
            reviewed_by="user_risk_mgr",
            rationale="Risks verified again",
            security_context=ctx_approver
        )

    # 8. Check that business was added to active watchlist
    with open(temp_actions_file, "r") as f:
        store = json.load(f)
        assert "BUS_001" in store["watchlist"]

def test_persistence_atomic_preservation(temp_actions_file):
    # Setup database check helpers
    risk_result = {
        "risk_score": 0.85,
        "risk_tier": "RED",
        "scoring_mode": "ml_model",
        "model_version": "RandomForest",
        "feature_contributions": [],
        "provenance": {}
    }
    
    intervention_plan = {
        "evidence_codes": ["DELINQUENCY_RISK"],
        "recommended_playbook": "Contact client RM",
        "allowed_actions": ["manual review"]
    }

    ctx = SecurityContext(
        request_id="req_p", session_id="ses_1", user_id="user_rm",
        role="relationship_manager", requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )

    # Add a proposal
    create_watchlist_proposal("BUS_001", "2025-06", "user_rm", risk_result, intervention_plan, ctx)

    # Malform the file
    with open(temp_actions_file, "w") as f:
        f.write("{invalid_json:")

    # Read must fail with ValueError due to corruption
    with pytest.raises(ValueError, match="Persistence Corruption"):
        list_pending_watchlist_proposals(ctx)

def test_concurrent_writes(temp_actions_file):
    risk_result = {
        "risk_score": 0.85,
        "risk_tier": "RED",
        "scoring_mode": "ml_model",
        "model_version": "RandomForest",
        "feature_contributions": [],
        "provenance": {}
    }
    
    intervention_plan = {
        "evidence_codes": ["DELINQUENCY_RISK"],
        "recommended_playbook": "Contact client RM",
        "allowed_actions": ["manual review"]
    }

    ctx = SecurityContext(
        request_id="req_concurrent", session_id="ses_1", user_id="user_rm",
        role="relationship_manager", requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )

    # Launch multiple threads writing proposals concurrently to verify no records lost
    def write_worker(biz_id):
        create_watchlist_proposal(biz_id, "2025-06", "user_rm", risk_result, intervention_plan, ctx)

    threads = []
    for i in range(10):
        t = threading.Thread(target=write_worker, args=(f"BUS_{i:03d}",))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Load store and verify all 10 proposals are present
    with open(temp_actions_file, "r") as f:
        store = json.load(f)
        assert len(store["proposals"]) == 10
