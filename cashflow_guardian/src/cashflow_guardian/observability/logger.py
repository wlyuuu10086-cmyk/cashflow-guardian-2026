import logging
import json
from typing import Any, Dict, Optional
from cashflow_guardian.security.redaction import redact_sensitive_data

# Fields to mask according to policies.yaml
MASKED_FIELDS = {"business_name", "transaction_memo", "review_notes", "reason", "rationale"}

class PiiMaskingFormatter(logging.Formatter):
    """Logging Formatter that masks PII and credentials from structured log dicts."""
    def format(self, record: logging.LogRecord) -> str:
        # If record msg is a dict, we process and redact it
        if isinstance(record.msg, dict):
            clean_msg, _ = redact_sensitive_data(record.msg)
            # Mask specific field keys
            for k in list(clean_msg.keys()):
                if k in MASKED_FIELDS:
                    clean_msg[k] = "[MASKED]"
            record.msg = clean_msg
            
        elif isinstance(record.msg, str):
            clean_msg, _ = redact_sensitive_data(record.msg)
            record.msg = clean_msg
            
        return super().format(record)

def get_structured_logger(name: str) -> logging.Logger:
    """Returns a pre-configured logger with PII and credential masking handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = PiiMaskingFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger

# Global default structured logger
app_logger = get_structured_logger("cashflow_guardian")
