from typing import Dict, Any, Optional, List
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk
from .portfolio import make_safe_error

def score_cashflow_risk_tool(
    business_id: str,
    as_of_month: str
) -> Dict[str, Any]:
    """Invokes predictive model to score SME 60-day cash stress probability."""
    try:
        res = score_cashflow_risk(
            business_id=business_id,
            month=as_of_month
        )
        # Ensure status is success
        res["status"] = "success"
        return res
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e))
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", "An internal system error occurred.")
