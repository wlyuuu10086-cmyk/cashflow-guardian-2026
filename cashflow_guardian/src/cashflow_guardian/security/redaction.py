import re
import os
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel

# Regex patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
# Absolute path regex (Windows and Linux)
PATH_RE = re.compile(r"(?:[a-zA-Z]:[\\/][a-zA-Z0-9_.\-\\/]+|(?:\b|^)/[a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-\\/]+)")
# Stack trace indicators
STACK_TRACE_INDICATOR = "traceback (most recent call last)"

# Sensitive key names for dict/model keys
SENSITIVE_KEY_PATTERNS = ["api_key", "secret", "password", "token", "credential", "conn_str", "database_path", "connection"]

def get_sensitive_env_values() -> List[str]:
    """Collects sensitive environment variable values to redact from any output strings."""
    sensitive_vals = []
    for k, v in os.environ.items():
        k_upper = k.upper()
        if any(term in k_upper for term in ["KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL", "API", "URL", "AUTH"]):
            if len(v) > 3:  # Only redact non-trivial values
                sensitive_vals.append(v)
    return sensitive_vals

def redact_string(val: str) -> Tuple[str, List[str], int]:
    """Redacts PII, absolute paths, stack traces, and credentials inside a string."""
    redacted = val
    redacted_keys = []
    count = 0
    
    # 1. Stack trace redaction
    if STACK_TRACE_INDICATOR in redacted.lower():
        redacted = "[REDACTED STACK TRACE]"
        redacted_keys.append("stack_trace")
        return redacted, redacted_keys, 1

    # 2. Basic database connection string detection
    db_conn_patterns = [r"[a-zA-Z0-9_\-]+://[^@]+:[^@]+@[^\s]+", r"duckdb\.connect\([^\)]*\)"]
    for pattern in db_conn_patterns:
        matches = re.findall(pattern, redacted)
        for match in matches:
            redacted = redacted.replace(match, "[REDACTED_CONNECTION_STRING]")
            redacted_keys.append("connection_string")
            count += 1

    # 3. Email redaction
    emails = EMAIL_RE.findall(redacted)
    if emails:
        for email in emails:
            redacted = redacted.replace(email, "[REDACTED_EMAIL]")
            redacted_keys.append("email")
            count += 1
            
    # 4. Phone redaction
    phones = PHONE_RE.findall(redacted)
    if phones:
        for phone in phones:
            # Prevent matching plain short numbers
            if len(phone.strip()) >= 7:
                redacted = redacted.replace(phone, "[REDACTED_PHONE]")
                redacted_keys.append("phone")
                count += 1

    # 5. Path redaction
    paths = PATH_RE.findall(redacted)
    if paths:
        for path in paths:
            # Do not redact short normal directories like '/tmp' or '/usr' if not absolute-like
            if len(path) > 3:
                redacted = redacted.replace(path, "[REDACTED_PATH]")
                redacted_keys.append("absolute_path")
                count += 1

    # 6. Env variables values redaction
    for env_val in get_sensitive_env_values():
        if env_val in redacted:
            redacted = redacted.replace(env_val, "[REDACTED_SECRET]")
            redacted_keys.append("secret_credential")
            count += 1

    return redacted, redacted_keys, count

def redact_sensitive_data(value: Any) -> Tuple[Any, Dict[str, Any]]:
    """Recursively redacts sensitive data (PII, credentials, absolute paths, stack traces).
    
    Works for strings, dicts, lists, Pydantic models, and exceptions.
    Returns:
        Tuple[redacted_value, metadata_dict]
    """
    metadata = {"redacted_keys": [], "redacted_count": 0}
    
    def merge_metadata(sub_keys: List[str], sub_count: int):
        for k in sub_keys:
            if k not in metadata["redacted_keys"]:
                metadata["redacted_keys"].append(k)
        metadata["redacted_count"] += sub_count

    if isinstance(value, str):
        red_val, keys, cnt = redact_string(value)
        merge_metadata(keys, cnt)
        return red_val, metadata

    elif isinstance(value, dict):
        redacted_dict = {}
        for k, v in value.items():
            k_str = str(k).lower()
            # If the key name is sensitive, redact its value completely
            if any(term in k_str for term in SENSITIVE_KEY_PATTERNS):
                redacted_dict[k] = "[REDACTED_SENSITIVE_FIELD]"
                merge_metadata(["sensitive_field"], 1)
            else:
                red_v, sub_meta = redact_sensitive_data(v)
                redacted_dict[k] = red_v
                merge_metadata(sub_meta["redacted_keys"], sub_meta["redacted_count"])
        return redacted_dict, metadata

    elif isinstance(value, list):
        redacted_list = []
        for item in value:
            red_item, sub_meta = redact_sensitive_data(item)
            redacted_list.append(red_item)
            merge_metadata(sub_meta["redacted_keys"], sub_meta["redacted_count"])
        return redacted_list, metadata

    elif isinstance(value, BaseModel):
        # Handle Pydantic models
        model_dict = value.model_dump()
        red_dict, sub_meta = redact_sensitive_data(model_dict)
        merge_metadata(sub_meta["redacted_keys"], sub_meta["redacted_count"])
        try:
            # Recreate model if possible
            red_model = value.__class__(**red_dict)
            return red_model, metadata
        except Exception:
            # Return dict representation if recreation fails
            return red_dict, metadata

    elif isinstance(value, Exception):
        # Redact exception representation
        err_msg = str(value)
        red_msg, keys, cnt = redact_string(err_msg)
        merge_metadata(keys, cnt)
        return f"{value.__class__.__name__}: {red_msg}", metadata

    return value, metadata
