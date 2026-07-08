import pytest
import os
import json
import tempfile
import logging
from cashflow_guardian.observability.schemas import AuditEvent
from cashflow_guardian.observability.audit_log import log_audit_event
from cashflow_guardian.observability.trace_store import global_trace_store
from cashflow_guardian.observability.logger import get_structured_logger

@pytest.fixture
def temp_audit_dir():
    """Provides a temporary audit log directory to ensure test isolation."""
    old_env = os.environ.get("CASHFLOW_GUARDIAN_AUDIT_DIR")
    temp_dir = tempfile.mkdtemp()
    os.environ["CASHFLOW_GUARDIAN_AUDIT_DIR"] = temp_dir
    yield temp_dir
    # Cleanup
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

def test_trace_store():
    global_trace_store.clear()
    trace_id = "trace_abc123"
    request_id = "req_999"

    global_trace_store.create_trace(trace_id, request_id)
    global_trace_store.add_step(trace_id, "request_received", {"tool": "dummy"})
    global_trace_store.add_step(trace_id, "security_validation")
    global_trace_store.add_step(trace_id, "tool_completed")

    trace = global_trace_store.get_trace(trace_id)
    assert trace is not None
    assert trace.request_id == request_id
    assert len(trace.steps) == 3
    assert trace.steps[0].step_name == "request_received"
    assert trace.steps[1].step_name == "security_validation"
    assert trace.steps[2].step_name == "tool_completed"
    # Verify ordering is preserved
    assert trace.steps[0].timestamp <= trace.steps[1].timestamp <= trace.steps[2].timestamp

def test_structured_logger():
    # Test logger formats and masks PII/memos
    logger = get_structured_logger("test_pii_logger")
    
    # We can capture stream output if needed, but we can verify the formatter logic directly.
    from cashflow_guardian.observability.logger import PiiMaskingFormatter
    formatter = PiiMaskingFormatter()
    
    # Dictionary log
    record_dict = logging.LogRecord("name", logging.INFO, "path", 10, {
        "business_name": "SME Company Inc",
        "transaction_memo": "Invoice pay secret_api_key_123",
        "risk_score": 0.85
    }, (), None)
    
    formatted_dict_str = formatter.format(record_dict)
    # Check that business_name and transaction_memo are masked/redacted
    assert "SME Company Inc" not in formatted_dict_str
    assert "secret_api_key_123" not in formatted_dict_str
    assert "[MASKED]" in formatted_dict_str or "[REDACTED]" in formatted_dict_str

def test_audit_logging_persistence(temp_audit_dir):
    event = AuditEvent(
        event_id="evt_test",
        timestamp="2026-07-03T18:16:34Z",
        request_id="req_test",
        session_id="ses_test",
        user_id="user_test",
        role="relationship_manager",
        event_type="policy_evaluation",
        tool_name="get_portfolio_snapshot",
        business_id="BUS_001",
        decision="allowed",
        policy_codes=["POLICY_TOOL_ALLOWED"],
        approval_required=False,
        metadata={"token": "sensitive_token_abc"}  # Should be redacted
    )

    log_audit_event(event)

    # Verify file was written
    target_path = os.path.join(temp_audit_dir, "policy_events.jsonl")
    assert os.path.exists(target_path)

    with open(target_path, "r", encoding="utf-8") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["event_id"] == "evt_test"
        # Verify metadata token key got redacted
        assert "sensitive_token_abc" not in line
        assert data["redaction_applied"] is True

def test_audit_fail_closed_vs_fail_safe(temp_audit_dir):
    event_policy = AuditEvent(
        event_id="evt_policy",
        timestamp="2026-07-03T18:16:34Z",
        request_id="req_p",
        session_id="ses_p",
        user_id="user_p",
        role="analyst",
        event_type="policy_evaluation",
        tool_name="get_portfolio_snapshot"
    )

    event_hitl = AuditEvent(
        event_id="evt_hitl",
        timestamp="2026-07-03T18:16:34Z",
        request_id="req_h",
        session_id="ses_h",
        user_id="user_h",
        role="risk_manager",
        event_type="proposal_approved"
    )

    # Override audit directory to an invalid/unwritable location
    os.environ["CASHFLOW_GUARDIAN_AUDIT_DIR"] = "D:\\invalid|<dir>|path"

    # 1. Non-sensitive action (policy evaluation) must fail safe (i.e. does not raise exception)
    try:
        log_audit_event(event_policy, fail_closed=False)
    except Exception as e:
        pytest.fail(f"Non-sensitive audit event failed closed instead of failing safe: {e}")

    # 2. Sensitive action (HITL approval) must fail closed (i.e. raises IOError)
    with pytest.raises(IOError, match="Critical Audit Failure"):
        log_audit_event(event_hitl, fail_closed=True)
