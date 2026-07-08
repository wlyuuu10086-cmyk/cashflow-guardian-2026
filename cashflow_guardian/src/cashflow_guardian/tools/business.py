from typing import Dict, Any, Optional, List
import cashflow_guardian.data_engine as de
from .portfolio import make_safe_error

def get_business_history_tool(
    business_id: str,
    as_of_month: str,
    months: int = 6
) -> Dict[str, Any]:
    """Exposes point-in-time safe business financial history query."""
    try:
        res = de.repository.get_business_history(
            business_id=business_id,
            as_of_month=as_of_month,
            months=months
        )
        return {
            "status": "success",
            "business_id": res.business_id,
            "history_months": res.history_months,
            "snapshots": [snap.model_dump() for snap in res.snapshots],
            "provenance": res.provenance.model_dump()
        }
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e))
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", "An internal system error occurred.")

def check_business_data_quality_tool(
    business_id: str,
    as_of_month: str
) -> Dict[str, Any]:
    """Evaluates business data completeness and quality checks."""
    try:
        res = de.quality.check_business_data_quality(
            business_id=business_id,
            as_of_month=as_of_month
        )
        return {
            "status": "success",
            "dq_status": res.status,
            "can_build_features": res.can_build_features,
            "missing_fields": res.missing_fields,
            "missing_months": res.missing_months,
            "transaction_gaps": res.transaction_gaps,
            "has_sufficient_history": res.has_sufficient_history,
            "errors": res.errors,
            "warnings": res.warnings,
            "provenance": res.provenance.model_dump() if res.provenance else None
        }
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e))
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", "An internal system error occurred.")
