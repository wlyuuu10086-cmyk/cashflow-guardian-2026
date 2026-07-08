from typing import Dict, Any, Optional, List
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk
from cashflow_guardian.benchmark_engine.comparison import compare_business_with_peers
from cashflow_guardian.scenario_engine.simulation import simulate_cashflow_scenario
from cashflow_guardian.intervention_engine.recommendations import draft_intervention_plan
from .portfolio import make_safe_error

def draft_intervention_plan_tool(
    business_id: str,
    as_of_month: str,
    include_scenario: bool = False,
    scenario_parameters: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Retrieves business risks and benchmarks to formulate draft intervention recommendations."""
    try:
        # 1. Fetch risk prediction
        risk_res = score_cashflow_risk(business_id, as_of_month)
        
        # 2. Fetch peer benchmark
        bench_res = compare_business_with_peers(business_id, as_of_month)
        
        # 3. Handle optional scenario simulation
        scen_res = None
        if include_scenario:
            params = scenario_parameters or {}
            scen_res = simulate_cashflow_scenario(
                business_id=business_id,
                as_of_month=as_of_month,
                inflow_change_pct=params.get("inflow_change_pct", 0.0),
                outflow_change_pct=params.get("outflow_change_pct", 0.0),
                collection_delay_change_days=params.get("collection_delay_change_days", 0.0),
                payroll_change_pct=params.get("payroll_change_pct", 0.0),
                debt_service_change_pct=params.get("debt_service_change_pct", 0.0)
            )
            
        # 4. Draft playbook plan
        plan = draft_intervention_plan(
            business_id=business_id,
            as_of_month=as_of_month,
            risk_result=risk_res,
            benchmark_result=bench_res,
            scenario_result=scen_res
        )
        
        return {
            "status": "success",
            "business_id": plan.business_id,
            "as_of_month": plan.as_of_month,
            "risk_tier": plan.risk_tier,
            "risk_score": float(plan.risk_score),
            "evidence_codes": plan.evidence_codes,
            "recommended_draft_actions": [rec.model_dump() for rec in plan.recommended_draft_actions],
            "priority": plan.priority,
            "rationale_codes": plan.rationale_codes,
            "human_approval_required": plan.human_approval_required,
            "prohibited_actions": plan.prohibited_actions,
            "warnings": plan.warnings
        }
        
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e))
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", f"An internal system error occurred: {str(e)}")
