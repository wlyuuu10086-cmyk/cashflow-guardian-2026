import pytest
import os
import tempfile
import duckdb
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.watchlist import (
    create_watchlist_proposal,
    review_watchlist_proposal,
    list_pending_watchlist_proposals,
    get_active_watchlist
)
from cashflow_guardian.data_engine.connection import get_database_path, check_database_health

@pytest.fixture
def temp_actions_file():
    """Provides a temporary file path for demo actions to ensure test isolation."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    old_env = os.environ.get("CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH")
    os.environ["CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH"] = path
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    if old_env is not None:
        os.environ["CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH"] = old_env
    else:
        os.environ.pop("CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH", None)

@pytest.fixture
def temp_audit_dir():
    """Provides a temporary audit log directory to ensure test isolation."""
    old_env = os.environ.get("CASHFLOW_GUARDIAN_AUDIT_DIR")
    temp_dir = tempfile.mkdtemp()
    os.environ["CASHFLOW_GUARDIAN_AUDIT_DIR"] = temp_dir
    yield temp_dir
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(temp_dir)
    if old_env is not None:
        os.environ["CASHFLOW_GUARDIAN_AUDIT_DIR"] = old_env
    else:
        os.environ.pop("CASHFLOW_GUARDIAN_AUDIT_DIR", None)

def test_hitl_watchlist_workflow_immutability(temp_actions_file, temp_audit_dir):
    # 1. Record DuckDB metadata before workflow
    db_path = get_database_path()
    initial_stat = os.stat(db_path)
    initial_size = initial_stat.st_size
    
    # Capture initial row counts
    health_before = check_database_health()
    assert health_before.database_available is True
    initial_counts = dict(health_before.row_counts)

    # 2. Execute HITL Watchlist workflow
    risk_result = {
        "risk_score": 0.85,
        "risk_tier": "RED",
        "scoring_mode": "ml_model",
        "model_version": "RandomForest",
        "feature_contributions": [],
        "provenance": {"future_data_used": False, "warnings": []}
    }
    
    intervention_plan = {
        "evidence_codes": ["DELINQUENCY_RISK"],
        "recommended_playbook": "Contact client RM",
        "allowed_actions": ["manual review"]
    }

    ctx_proposer = SecurityContext(
        request_id="req_hitl_propose", session_id="ses_1", user_id="user_rm",
        role="relationship_manager", requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )

    # Propose
    prop = create_watchlist_proposal(
        business_id="BUS_001",
        as_of_month="2025-06",
        proposed_by="user_rm",
        risk_result=risk_result,
        intervention_plan=intervention_plan,
        security_context=ctx_proposer,
        idempotency_key="hitl_idem_1"
    )
    
    proposal_id = prop["proposal_id"]
    assert prop["status"] == "pending"

    # Reviewer tries to self-approve and fails
    ctx_self = SecurityContext(
        request_id="req_self_app", session_id="ses_1", user_id="user_rm",
        role="risk_manager", requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )
    with pytest.raises(ValueError, match="Conflict of interest"):
        review_watchlist_proposal(
            proposal_id=proposal_id,
            decision="approve",
            reviewed_by="user_rm",
            rationale="Approved by self",
            security_context=ctx_self
        )

    # Approved by another Risk Manager
    ctx_risk_mgr = SecurityContext(
        request_id="req_hitl_approve", session_id="ses_1", user_id="user_risk_mgr",
        role="risk_manager", requested_tool="approve_or_reject_watchlist_action",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local"
    )

    review_res = review_watchlist_proposal(
        proposal_id=proposal_id,
        decision="approve",
        reviewed_by="user_risk_mgr",
        rationale="Evidence of delinquent invoice repayment, high risk score.",
        security_context=ctx_risk_mgr
    )

    assert review_res["updated_status"] == "approved"
    assert "BUS_001" in get_active_watchlist()

    # 3. Verify DuckDB remains completely unchanged
    health_after = check_database_health()
    after_counts = dict(health_after.row_counts)
    
    after_stat = os.stat(db_path)
    after_size = after_stat.st_size

    # Fail validation if any source mutation is detected
    assert after_size == initial_size, f"Database file size changed from {initial_size} to {after_size}."
    assert after_counts == initial_counts, f"Database row counts changed: Before={initial_counts}, After={after_counts}."
