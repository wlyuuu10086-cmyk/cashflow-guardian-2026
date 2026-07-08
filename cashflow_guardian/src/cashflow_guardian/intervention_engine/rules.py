from typing import List, Dict, Any, Tuple, Optional
from .schemas import InterventionRecommendation

PROHIBITED_ACTIONS = [
    "automatic credit-limit reduction",
    "automatic loan rejection",
    "automatic collections action",
    "customer email",
    "payment execution",
    "legal escalation",
    "account freezing"
]

def evaluate_rules(
    business_id: str,
    as_of_month: str,
    risk_result: Dict[str, Any],
    benchmark_result: Any,
    scenario_result: Optional[Any] = None
) -> Tuple[List[InterventionRecommendation], List[str], List[str], str, bool, List[str]]:
    """Evaluates policy rules deterministically based on risk, benchmark, and scenario inputs.
    
    Returns:
        Tuple of (recommendations, evidence_codes, rationale_codes, overall_priority, human_approval_required, warnings)
    """
    evidence_codes = []
    rationale_codes = []
    recs = []
    warnings = []
    human_approval_required = False
    
    # Initialize overall priority based on risk tier
    risk_tier = risk_result.get("risk_tier", "GREEN")
    risk_score = risk_result.get("risk_score", 0.0)
    
    if risk_tier == "RED":
        overall_priority = "high"
        recs.append(InterventionRecommendation(
            action="contact relationship manager for manual review",
            priority="high",
            description="Business is flagged as RED (high risk), requiring immediate manual review by the relationship manager."
        ))
        recs.append(InterventionRecommendation(
            action="propose demonstration watchlist review",
            priority="high",
            description="Propose adding the business to the watch list due to high predictive cash stress."
        ))
        human_approval_required = True
        evidence_codes.append("RED_RISK_TIER")
        rationale_codes.append("RED_RISK_TIER_INTERVENTION")
    elif risk_tier == "AMBER":
        overall_priority = "medium"
        recs.append(InterventionRecommendation(
            action="increase monitoring frequency",
            priority="medium",
            description="Business is in the AMBER (medium risk) tier. Increase review frequency."
        ))
        recs.append(InterventionRecommendation(
            action="request updated cash-flow information",
            priority="medium",
            description="Request recent bank statements and cash flow projections to clarify stress signals."
        ))
        evidence_codes.append("AMBER_RISK_TIER")
        rationale_codes.append("AMBER_RISK_TIER_MONITORING")
    else:
        overall_priority = "low"
        recs.append(InterventionRecommendation(
            action="continue routine monitoring",
            priority="low",
            description="Business is low risk. Continue standard portfolio monitoring."
        ))
        evidence_codes.append("GREEN_RISK_TIER")
        rationale_codes.append("ROUTINE_MONITORING")
        
    # Check repayment burden pct from benchmark metrics
    repay_burden_comp = benchmark_result.metrics.get("repayment_burden")
    if repay_burden_comp and repay_burden_comp.business_value is not None:
        if repay_burden_comp.business_value > 0.25: # exceeds 25% warning threshold
            recs.append(InterventionRecommendation(
                action="review repayment schedule",
                priority="medium",
                description=f"Monthly scheduled repayments exceed 25% of cash inflows (Business value: {repay_burden_comp.business_value * 100.0:.1f}%)."
            ))
            evidence_codes.append("HIGH_REPAYMENT_BURDEN")
            rationale_codes.append("DEBT_SERVICE_BURDEN_MITIGATION")
            if overall_priority == "low":
                overall_priority = "medium"
                
    # Check collection delay gap from benchmark
    coll_days_comp = benchmark_result.metrics.get("collection_days")
    if coll_days_comp and coll_days_comp.absolute_gap is not None:
        if coll_days_comp.absolute_gap > 15.0 or (coll_days_comp.business_value and coll_days_comp.business_value > 45.0):
            recs.append(InterventionRecommendation(
                action="verify large outstanding invoices",
                priority="medium",
                description=f"Collection days are significantly higher than peer benchmarks (Business value: {coll_days_comp.business_value:.1f} days, Peer median: {coll_days_comp.peer_value:.1f} days)."
            ))
            evidence_codes.append("COLLECTION_DELAY_GAP")
            rationale_codes.append("RECEIVABLES_VERIFICATION")
            if overall_priority == "low":
                overall_priority = "medium"
                
    # Check for active delinquency (e.g. max_dpd > 0)
    overdraft_comp = benchmark_result.metrics.get("overdraft_days")
    if overdraft_comp and overdraft_comp.business_value is not None and overdraft_comp.business_value > 2.0:
        evidence_codes.append("ACTIVE_OVERDRAFT")
        recs.append(InterventionRecommendation(
            action="assess short-term liquidity support eligibility",
            priority="medium",
            description=f"Active overdraft days ({overdraft_comp.business_value:.0f} days) detected in the current month."
        ))
        rationale_codes.append("LIQUIDITY_SUPPORT_ELIGIBILITY")
        if overall_priority == "low":
            overall_priority = "medium"
            
    # Check net cash flow trend
    trend_comp = benchmark_result.metrics.get("trend")
    if trend_comp and trend_comp.business_value is not None and trend_comp.business_value < -5000.0:
        evidence_codes.append("DECLINING_CASH_FLOW")
        recs.append(InterventionRecommendation(
            action="assess short-term liquidity support eligibility",
            priority="medium",
            description=f"Declining 3-month net cash flow trend ({trend_comp.business_value:+.2f}) indicates potential cash depletion."
        ))
        rationale_codes.append("CASH_FLOW_DECLINE")
        if overall_priority == "low":
            overall_priority = "medium"
            
    # Check data quality issues
    dq_warnings = risk_result.get("warnings", [])
    if any("data quality" in w.lower() or "insufficient history" in w.lower() for w in dq_warnings):
        recs.append(InterventionRecommendation(
            action="request updated cash-flow information",
            priority="medium",
            description="Recent historical gaps or data quality warnings require updated cash flow documentation."
        ))
        evidence_codes.append("DATA_QUALITY_WARNING")
        rationale_codes.append("DATA_INTEGRITY_VERIFICATION")
        if overall_priority == "low":
            overall_priority = "medium"
            
    # Check Scenario Deterioration
    if scenario_result:
        if scenario_result.simulated.risk_tier == "RED" or scenario_result.risk_score_change > 0.15:
            recs.append(InterventionRecommendation(
                action="assess short-term liquidity support eligibility",
                priority="high",
                description=f"Scenario simulation indicates high vulnerability to cash flow shocks, causing transition to RED risk tier (Risk score increase: {scenario_result.risk_score_change * 100.0:+.1f}%)."
            ))
            evidence_codes.append("SCENARIO_DETERIORATION")
            rationale_codes.append("SHOCK_VULNERABILITY")
            overall_priority = "high"
            
    # Ensure uniqueness of recommendations list
    seen_recs = set()
    unique_recs = []
    for r in recs:
        if r.action not in seen_recs:
            seen_recs.add(r.action)
            unique_recs.append(r)
            
    return unique_recs, evidence_codes, rationale_codes, overall_priority, human_approval_required, warnings
