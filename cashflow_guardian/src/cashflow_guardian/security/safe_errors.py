from typing import List, Optional
from .schemas import SafeError
from .redaction import redact_sensitive_data

class CashFlowGuardianSecurityError(Exception):
    """Custom security exception for CashFlow Guardian."""
    def __init__(self, message: str, error_code: str = "SECURITY_VIOLATION", policy_codes: Optional[List[str]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.policy_codes = policy_codes or []

def translate_to_safe_error(exception: Exception, request_id: str) -> SafeError:
    """Translates raw system exceptions to a SafeError model.
    
    This translation prevents raw Python tracebacks, database connection details,
    absolute paths, and secrets from leaking to the Agent. It applies redaction 
    and returns a sanitized SafeError.
    
    Any tracebacks are suppressed and logged internally, never exposed to the caller.
    """
    error_code = "INTERNAL_ERROR"
    message = "An internal system error occurred."
    retryable = False
    invalid_fields = []
    policy_codes = []
    warnings = []

    # Handle known validation/security errors
    from cashflow_guardian.security.validation import SecurityValidationError
    from cashflow_guardian.data_engine.validators import ValidationError
    
    # Check for known errors and map error codes
    if isinstance(exception, SecurityValidationError):
        error_code = "SECURITY_VALIDATION_ERROR"
        message = str(exception)
        policy_codes = ["SECURITY_INVALID_INPUT"]
    elif isinstance(exception, ValidationError):
        error_code = "VALIDATION_ERROR"
        message = str(exception)
        policy_codes = ["SECURITY_INVALID_INPUT"]
        # Extract invalid fields if available
        if hasattr(exception, "invalid_fields"):
            invalid_fields = getattr(exception, "invalid_fields") or []
    elif isinstance(exception, CashFlowGuardianSecurityError):
        error_code = exception.error_code
        message = str(exception)
        policy_codes = exception.policy_codes
    elif isinstance(exception, PermissionError):
        error_code = "PERMISSION_DENIED"
        message = "Permission denied for this operation."
        policy_codes = ["POLICY_TOOL_DENIED"]
    elif isinstance(exception, ConnectionError):
        error_code = "DATABASE_ERROR"
        message = "The database is temporarily unreachable."
        retryable = True
        policy_codes = ["POLICY_DATABASE_UNREACHABLE"]
    else:
        # Generic error message for unhandled system exceptions
        message = str(exception)
        
    # Apply redaction to the message to ensure no secrets or local paths are exposed
    redacted_message, redact_meta = redact_sensitive_data(message)
    if redact_meta.get("redacted_count", 0) > 0 or "REDACTED" in redacted_message:
        policy_codes.append("SECURITY_UNSAFE_ERROR_REDACTED")
        if error_code == "INTERNAL_ERROR":
            redacted_message = "An internal system error occurred."
        else:
            redacted_message = "An error occurred, but sensitive details were redacted for security."

    # Prevent traceback leaks
    return SafeError(
        error_code=error_code,
        message=redacted_message,
        retryable=retryable,
        invalid_fields=invalid_fields,
        policy_codes=policy_codes,
        warnings=warnings,
        request_id=request_id
    )
