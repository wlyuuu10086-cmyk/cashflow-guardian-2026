import os
import json
import threading
from typing import Dict, Any, Optional
from .schemas import AuditEvent
from cashflow_guardian.security.redaction import redact_sensitive_data

# Thread lock for audit log writes
_AUDIT_LOCK = threading.Lock()

def _get_audit_directory() -> str:
    """Resolves the audit logs directory path, allowing env override for tests."""
    if "CASHFLOW_GUARDIAN_AUDIT_DIR" in os.environ:
        return os.environ["CASHFLOW_GUARDIAN_AUDIT_DIR"]
    
    from cashflow_guardian.data_engine.connection import get_repo_root
    return str(get_repo_root() / "cashflow_guardian" / "artifacts" / "audit")

def log_audit_event(event: AuditEvent, fail_closed: bool = False) -> None:
    """Logs an AuditEvent to the corresponding JSONL file under the audit directory.
    
    Ensures:
      1. Safe recursive redaction of secrets, paths, and tracebacks before writing.
      2. Thread-safe append-only persistence.
      3. Fail-closed behavior for sensitive operations (like HITL reviews) and
         fail-safe behavior for non-sensitive operations (like policy denials).
    """
    audit_dir = _get_audit_directory()
    
    # Determine target file name based on event type
    if event.event_type == "policy_evaluation":
        file_name = "policy_events.jsonl"
    elif event.event_type in ["proposal_created", "proposal_approved", "proposal_rejected"]:
        file_name = "hitl_events.jsonl"
        # HITL actions are sensitive and must fail closed by default if not specified
        fail_closed = True
    elif event.event_type in ["security_block", "security_warning", "prompt_injection_warning"]:
        file_name = "security_events.jsonl"
    else:
        file_name = "security_events.jsonl"

    target_path = os.path.join(audit_dir, file_name)

    try:
        # 1. Convert event to dict and recursively redact sensitive data
        event_dict = event.model_dump()
        
        # Redact the event payload recursively
        redacted_dict, redact_meta = redact_sensitive_data(event_dict)
        
        # Set redaction_applied flag if secrets were redacted
        if redact_meta.get("redacted_count", 0) > 0:
            redacted_dict["redaction_applied"] = True
            
        # Omit raw tool results / credentials / tracebacks / db paths (already done by redactor, but be explicit)
        # Ensure metadata is clean
        if "metadata" in redacted_dict:
            # Mask sensitive things from metadata
            clean_meta, _ = redact_sensitive_data(redacted_dict["metadata"])
            # Remove any raw database connections, models, or SQL
            for key in list(clean_meta.keys()):
                if key in ["db_conn", "conn", "model", "sql_query", "raw_sql", "traceback"]:
                    clean_meta.pop(key)
            redacted_dict["metadata"] = clean_meta

        # Convert to single line JSON
        log_line = json.dumps(redacted_dict) + "\n"

        # 2. Thread-safe append write
        with _AUDIT_LOCK:
            os.makedirs(audit_dir, exist_ok=True)
            with open(target_path, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()

    except Exception as e:
        # Documented distinction:
        # Successful sensitive actions (like HITL approval) must fail closed if writing audit log fails.
        # Policy denials / validations can fail-safe and log error to stderr.
        if fail_closed:
            raise IOError(f"Critical Audit Failure: Failed to write audit log for sensitive action: {e}")
        else:
            # Fail-safe: print to stderr but let execution continue
            import sys
            sys.stderr.write(f"Audit log write failed (fail-safe): {e}\n")
