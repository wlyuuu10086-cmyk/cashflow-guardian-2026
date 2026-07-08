import re
import os
import math
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

class SecurityValidationError(ValueError):
    """Exception raised when security input validation fails."""
    pass

def get_repo_root() -> Path:
    """Resolves the repository root dynamically."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent

def get_configured_max_month() -> str:
    """Determines the maximum allowed as-of month from env, config, or database."""
    # 1. Environment variable override
    if "CASHFLOW_GUARDIAN_MAX_MONTH" in os.environ:
        return os.environ["CASHFLOW_GUARDIAN_MAX_MONTH"]
    
    # 2. App configuration app.yaml or database.yaml demo cutoff
    try:
        repo_root = get_repo_root()
        config_path = repo_root / "cashflow_guardian" / "config" / "app.yaml"
        if not config_path.exists():
            config_path = repo_root / "config" / "app.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f)
                cutoff = cfg.get("app", {}).get("demo_cutoff_month") or cfg.get("demo_cutoff_month")
                if cutoff:
                    return cutoff
    except Exception:
        pass

    # 3. Database metadata maximum snapshot month
    try:
        from cashflow_guardian.data_engine.connection import get_readonly_connection
        from cashflow_guardian.data_engine.validators import get_db_month_range
        conn = get_readonly_connection()
        _, max_db_month = get_db_month_range(conn)
        conn.close()
        return max_db_month
    except Exception:
        pass
        
    # Default fallback
    return "2025-12"

def has_path_traversal(val: str) -> bool:
    """Checks if a string contains path traversal indicators."""
    # Look for patterns like .., ./, .\, /, \
    if ".." in val:
        return True
    return False

def is_absolute_path(val: str) -> bool:
    """Checks if a string represents an absolute path on Windows or Unix."""
    # Windows drive letter e.g. C:\ or C:/, or UNC path \\
    if re.match(r"^[a-zA-Z]:[\\/]", val):
        return True
    if val.startswith(r"\\"):
        return True
    # Unix root path (ignore single '/' if it represents something else, but here we block absolute paths)
    if val.startswith("/"):
        return True
    return False

def contains_serialized_python(val: str) -> bool:
    """Checks for serialized Python object markers (e.g. pickle format signatures)."""
    # Pickle protocol version 0-5 signature indicators
    if val.startswith("cos\n") or val.startswith("cbuiltins\n") or "cos\n" in val:
        return True
    if "pickle" in val.lower():
        # Check if looks like a base64 encoded pickle or raw pickle
        if re.search(r"(_pickle|cPickle|__main__|copy_reg)", val):
            return True
    return False

def validate_input_value(param_name: str, val: Any) -> None:
    """Recursively validates a parameter value to ensure it contains no malicious payloads."""
    if isinstance(val, str):
        # 1. Length constraint
        if len(val) > 2000:
            raise SecurityValidationError(f"Input parameter '{param_name}' exceeds maximum allowed length of 2000 characters.")
        
        # 2. Check for absolute paths
        if is_absolute_path(val):
            raise SecurityValidationError(f"Input parameter '{param_name}' contains prohibited absolute file path: '{val}'")
            
        # 3. Check for serialized python objects
        if contains_serialized_python(val):
            raise SecurityValidationError(f"Input parameter '{param_name}' contains suspected serialized Python objects.")

        # 4. Check for command injection characters
        command_chars = [";", "|", "&", "$", "`"]
        # Only reject command chars in identifier-like fields, but protect against them generally
        if param_name.endswith("_id") or param_name == "tool_name":
            for char in command_chars:
                if char in val:
                    raise SecurityValidationError(f"Prohibited command injection character '{char}' detected in '{param_name}'.")

        # 5. Check ID-like parameters strictly
        if param_name.endswith("_id") or param_name == "business_id" or param_name.endswith("_by") or param_name.endswith("_role") or param_name == "RM_id":
            # Strip and check length
            if len(val) > 64:
                raise SecurityValidationError(f"Identifier '{param_name}' exceeds maximum allowed length of 64 characters.")
            
            # Check path traversal
            if has_path_traversal(val) or "/" in val or "\\" in val:
                raise SecurityValidationError(f"Path traversal characters detected in identifier '{param_name}': '{val}'")
                
            # SQL Injection check on identifiers
            # Identifiers must only contain alphanumeric, underscore, hyphen or standard prefixes like req_, proposal_, etc.
            if not re.match(r"^[a-zA-Z0-9_\-:]+$", val):
                raise SecurityValidationError(f"Identifier '{param_name}' contains invalid or unsafe characters: '{val}'")
                
            # Check for SQL injection keywords in identifiers
            sql_keywords = ["SELECT", "UNION", "INSERT", "DELETE", "UPDATE", "DROP", "ALTER", "CREATE", "OR", "AND"]
            val_upper = val.upper()
            for kw in sql_keywords:
                if re.search(r"\b" + kw + r"\b", val_upper):
                    raise SecurityValidationError(f"SQL keyword '{kw}' is prohibited in identifier fields.")

        # 6. Check month parameters
        if param_name in ["month", "as_of_month"]:
            if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", val):
                raise SecurityValidationError(f"Month parameter '{param_name}' must be in YYYY-MM format.")
            
            max_m = get_configured_max_month()
            if val > max_m:
                raise SecurityValidationError(f"Requested month '{val}' is beyond the maximum configured data boundary of {max_m}.")

    elif isinstance(val, (int, float)):
        # Check for NaN and Infinity
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                raise SecurityValidationError(f"Numerical parameter '{param_name}' contains invalid NaN or Infinity value.")

    elif isinstance(val, list):
        if len(val) > 100:
            raise SecurityValidationError(f"List parameter '{param_name}' exceeds maximum allowed length of 100 elements.")
        for idx, item in enumerate(val):
            validate_input_value(f"{param_name}[{idx}]", item)

    elif isinstance(val, dict):
        if len(val) > 100:
            raise SecurityValidationError(f"Dict parameter '{param_name}' exceeds maximum allowed number of keys (100).")
        for k, v in val.items():
            if not isinstance(k, str):
                raise SecurityValidationError(f"Dict key in '{param_name}' must be a string.")
            validate_input_value(f"{param_name}.{k}", k)
            validate_input_value(f"{param_name}.{k}", v)

def validate_input_parameters(tool_name: str, arguments: Dict[str, Any]) -> None:
    """Validates all inputs for a given tool request. Fails closed on any security violation."""
    from cashflow_guardian.tools.registry import APPROVED_TOOL_NAMES
    
    # 1. Validate tool exists
    if tool_name not in APPROVED_TOOL_NAMES:
        raise SecurityValidationError(f"Unsupported or unregistered tool name: '{tool_name}'")

    # 2. Validate arguments
    for param_name, val in arguments.items():
        validate_input_value(param_name, val)
