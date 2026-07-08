import pytest
import os
import json
import tempfile
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.tools.registry import execute_tool_with_policy
from cashflow_guardian.observability.trace_store import global_trace_store

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

def test_audit_trace_workflow_success_path(temp_actions_file, temp_audit_dir):
    global_trace_store.clear()
    
    ctx = SecurityContext(
        request_id="req_trace_ok", session_id="ses_1", user_id="alice_rm",
        role="relationship_manager", requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local",
        metadata={"trace_id": "trace_ok_123"}
    )

    # Call tool successfully
    res = execute_tool_with_policy(
        security_context=ctx,
        tool_name="get_portfolio_snapshot",
        tool_arguments={"month": "2025-06", "limit": 1}
    )

    assert res.status == "success"

    # Verify trace steps are recorded
    trace = global_trace_store.get_trace("trace_ok_123")
    assert trace is not None
    steps = [step.step_name for step in trace.steps]
    
    # Trace steps must contain correct lifecycle events in order
    assert "request_received" in steps
    assert "security_validation" in steps
    assert "policy_decision" in steps
    assert "tool_selected" in steps
    assert "tool_started" in steps
    assert "tool_completed" in steps
    assert "response_produced" in steps

    # Verify audit files exist and are populated
    security_log_path = os.path.join(temp_audit_dir, "security_events.jsonl")
    assert os.path.exists(security_log_path)

    with open(security_log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 1  # tool execution success
        
        # Verify JSON validity and unique event IDs
        event_ids = []
        for line in lines:
            evt = json.loads(line)
            event_ids.append(evt["event_id"])
            assert evt["request_id"] == "req_trace_ok"
            assert evt["role"] == "relationship_manager"
            
        assert len(event_ids) == len(set(event_ids))  # unique IDs

def test_audit_trace_workflow_denied_path(temp_actions_file, temp_audit_dir):
    global_trace_store.clear()

    ctx = SecurityContext(
        request_id="req_trace_deny", session_id="ses_1", user_id="bob_admin",
        role="administrator", requested_tool="get_portfolio_snapshot",
        timestamp="2026-07-03T18:16:34Z", source="web", environment="local",
        metadata={"trace_id": "trace_deny_123"}
    )

    # Call tool and fail policy
    res = execute_tool_with_policy(
        security_context=ctx,
        tool_name="get_portfolio_snapshot",
        tool_arguments={"month": "2025-06"}
    )

    assert res.status == "denied"

    # Verify trace steps are truncated appropriately
    trace = global_trace_store.get_trace("trace_deny_123")
    assert trace is not None
    steps = [step.step_name for step in trace.steps]
    
    assert "request_received" in steps
    assert "security_validation" in steps
    assert "policy_decision" in steps
    assert "response_produced" in steps
    # Must not contain tool_started or completed since it was blocked
    assert "tool_started" not in steps
    assert "tool_completed" not in steps
