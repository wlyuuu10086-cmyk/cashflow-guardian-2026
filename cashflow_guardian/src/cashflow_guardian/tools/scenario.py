from typing import Dict, Any, Optional, List
from cashflow_guardian.scenario_engine.simulation import simulate_cashflow_scenario
from .portfolio import make_safe_error

def simulate_cashflow_scenario_tool(
    business_id: str,
    as_of_month: str,
    inflow_change_pct: float = 0.0,
    outflow_change_pct: float = 0.0,
    collection_delay_change_days: float = 0.0,
    payroll_change_pct: float = 0.0,
    debt_service_change_pct: float = 0.0
) -> Dict[str, Any]:
    """Runs point-in-time safe scenario simulation and risk prediction."""
    try:
        res = simulate_cashflow_scenario(
            business_id=business_id,
            as_of_month=as_of_month,
            inflow_change_pct=inflow_change_pct,
            outflow_change_pct=outflow_change_pct,
            collection_delay_change_days=collection_delay_change_days,
            payroll_change_pct=payroll_change_pct,
            debt_service_change_pct=debt_service_change_pct
        )
        return {
            "status": "success",
            "business_id": res.business_id,
            "as_of_month": res.as_of_month,
            "assumptions": res.assumptions,
            "baseline": res.baseline.model_dump(),
            "simulated": res.simulated.model_dump(),
            "risk_score_change": res.risk_score_change,
            "risk_tier_change": res.risk_tier_change,
            "scoring_mode": res.scoring_mode,
            "model_version": res.model_version,
            "warnings": res.warnings,
            "future_data_used": res.future_data_used,
            "collection_delay_details": res.collection_delay_details
        }
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e))
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", "An internal system error occurred.")
