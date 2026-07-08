import logging
from typing import Dict, Any, List

logger = logging.getLogger("cashflow_guardian.risk_engine")

class RiskAuditLog:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_prediction(
        self,
        business_id: str,
        month: str,
        risk_score: float,
        risk_tier: str,
        scoring_mode: str,
        warnings: List[str]
    ):
        entry = {
            "business_id": business_id,
            "month": month,
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "scoring_mode": scoring_mode,
            "warnings": warnings
        }
        self.logs.append(entry)
        
        # Log to python standard logging
        msg = f"Scored {business_id} on {month}: score={risk_score:.4f}, tier={risk_tier}, mode={scoring_mode}"
        if warnings:
            msg += f" | Warnings: {', '.join(warnings)}"
        logger.info(msg)

# Global audit logger instance
audit_logger = RiskAuditLog()
