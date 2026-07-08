import pytest
import os
import tempfile
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.tools.registry import (
    execute_tool_with_policy,
    get_tool_registry,
    APPROVED_TOOL_NAMES
)
from cashflow_guardian.policy.permissions import get_required_permission_for_tool

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

def test_execute_tool_with_policy_schema(temp_actions_file, temp_audit_dir):
    ctx_analyst = SecurityContext(
        request_id="req_schema_test",
        session_id="ses_1",
        user_id="user_analyst",
        role="analyst",
        requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z",
        source="web",
        environment="local"
    )

    # Execute a valid tool
    res = execute_tool_with_policy(
        security_context=ctx_analyst,
        tool_name="get_portfolio_snapshot",
        tool_arguments={"month": "2025-06", "limit": 5}
    )

    # 1. Verify schema conformanc
    assert res.request_id == "req_schema_test"
    assert res.tool_name == "get_portfolio_snapshot"
    assert res.allowed is True
    assert res.approval_required is False
    assert res.status == "success"
    assert res.result is not None
    assert res.safe_error is None
    assert "POLICY_TOOL_ALLOWED" in res.policy_codes
    assert res.audit_event_id.startswith("evt_")
    assert res.trace_id.startswith("trace_")

def test_execute_tool_with_policy_roles_enforcement(temp_actions_file, temp_audit_dir):
    ctx_admin = SecurityContext(
        request_id="req_admin_read",
        session_id="ses_1",
        user_id="user_admin",
        role="administrator",
        requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z",
        source="web",
        environment="local"
    )

    # Admin cannot read portfolio (permission portfolio.read is not in administrator allowed_permissions)
    res = execute_tool_with_policy(
        security_context=ctx_admin,
        tool_name="get_portfolio_snapshot",
        tool_arguments={"month": "2025-06"}
    )
    
    assert res.allowed is False
    assert res.status == "denied"
    assert "POLICY_PERMISSION_MISSING" in res.policy_codes
    assert res.safe_error is not None
    assert "Permission denied" in res.safe_error.message or "does not possess required permission" in res.safe_error.message

def test_execute_tool_with_policy_unapproved_or_forbidden_tools(temp_actions_file, temp_audit_dir):
    ctx_analyst = SecurityContext(
        request_id="req_forbid",
        session_id="ses_1",
        user_id="user_analyst",
        role="analyst",
        requested_tool="execute_sql",
        timestamp="2026-07-03T18:16:34Z",
        source="web",
        environment="local"
    )

    # SQL tool is forbidden and unapproved
    res = execute_tool_with_policy(
        security_context=ctx_analyst,
        tool_name="execute_sql",
        tool_arguments={"sql": "SELECT * FROM repayments"}
    )

    assert res.allowed is False
    assert res.status == "validation_error"  # blocked by input validation naming check
    assert res.safe_error is not None

def test_execute_tool_with_policy_approval_required_guard(temp_actions_file, temp_audit_dir):
    ctx_rm = SecurityContext(
        request_id="req_propose_direct",
        session_id="ses_1",
        user_id="user_rm",
        role="relationship_manager",
        requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z",
        source="web",
        environment="local"
    )

    # Proposing watchlist action requires approval flag in metadata, otherwise blocks as approval_required
    res = execute_tool_with_policy(
        security_context=ctx_rm,
        tool_name="propose_watchlist_action",
        tool_arguments={
            "business_id": "BUS_001",
            "month": "2025-06",
            "reason": "High risk",
            "RM_id": "user_rm"
        }
    )

    assert res.status == "approval_required"
    assert res.approval_required is True
    assert "POLICY_HUMAN_APPROVAL_REQUIRED" in res.policy_codes

    # Signed with approved=True allows execution
    ctx_rm_signed = SecurityContext(
        request_id="req_propose_signed",
        session_id="ses_1",
        user_id="user_rm",
        role="relationship_manager",
        requested_tool="propose_watchlist_action",
        timestamp="2026-07-03T18:16:34Z",
        source="web",
        environment="local",
        metadata={"approved": True}
    )

    # Let's mock a risk result and intervention draft
    # Wait, the tool propose_watchlist_action requires business_id, month, reason, RM_id.
    # Let's execute it!
    res_signed = execute_tool_with_policy(
        security_context=ctx_rm_signed,
        tool_name="propose_watchlist_action",
        tool_arguments={
            "business_id": "BUS_001",
            "month": "2025-06",
            "reason": "High risk",
            "RM_id": "user_rm"
        }
    )

    assert res_signed.status == "success"
    assert res_signed.result["status"] == "pending"
