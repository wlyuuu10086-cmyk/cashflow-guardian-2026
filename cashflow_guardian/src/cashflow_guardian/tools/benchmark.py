from typing import Dict, Any, Optional, List
from cashflow_guardian.benchmark_engine.comparison import compare_business_with_peers
from .portfolio import make_safe_error

def compare_with_peers_tool(
    business_id: str,
    as_of_month: str
) -> Dict[str, Any]:
    """Compares business metrics with medians of its industry/revenue-band peer group."""
    try:
        res = compare_business_with_peers(
            business_id=business_id,
            as_of_month=as_of_month
        )
        return {
            "status": "success",
            "business_id": res.business_id,
            "as_of_month": res.as_of_month,
            "peer_group": res.peer_group.model_dump(),
            "metrics": {k: v.model_dump() for k, v in res.metrics.items()},
            "provenance": res.provenance.model_dump(),
            "warnings": res.warnings
        }
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e))
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", "An internal system error occurred.")
