from typing import Dict, List, Any, Optional
from .schemas import InterventionPlan
from .rules import evaluate_rules, PROHIBITED_ACTIONS

def draft_intervention_plan(
    business_id: str,
    as_of_month: str,
    risk_result: Dict[str, Any],
    benchmark_result: Any,
    scenario_result: Optional[Any] = None
) -> InterventionPlan:
    """Drafts an intervention plan for a business based on its risk tier and financial benchmarks.
    
    This function evaluates deterministic policy rules. It does not write to the action database.
    """
    recs, evidence_codes, rationale_codes, priority, human_approval_required, warnings = evaluate_rules(
        business_id, as_of_month, risk_result, benchmark_result, scenario_result
    )
    
    return InterventionPlan(
        business_id=business_id,
        as_of_month=as_of_month,
        risk_tier=risk_result.get("risk_tier", "GREEN"),
        risk_score=risk_result.get("risk_score", 0.0),
        evidence_codes=evidence_codes,
        recommended_draft_actions=recs,
        priority=priority,
        rationale_codes=rationale_codes,
        human_approval_required=human_approval_required,
        prohibited_actions=PROHIBITED_ACTIONS,
        warnings=warnings
    )
