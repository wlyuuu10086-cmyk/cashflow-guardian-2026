from typing import List, Dict, Any
from .simulation import simulate_cashflow_scenario

def run_one_way_sensitivity(
    business_id: str,
    as_of_month: str,
    variable: str,
    values: List[float]
) -> List[Dict[str, Any]]:
    """Runs a series of scenarios modifying a single assumption variable over a grid of values.
    
    Supported variables:
        - inflow_change_pct
        - outflow_change_pct
        - collection_delay_change_days
    """
    allowed_vars = ["inflow_change_pct", "outflow_change_pct", "collection_delay_change_days"]
    if variable not in allowed_vars:
        raise ValueError(f"Variable '{variable}' is not supported for sensitivity analysis. Must be one of {allowed_vars}")
        
    if len(values) > 10:
        raise ValueError(f"Sensitivity grid is limited to a maximum of 10 values, got {len(values)}")
        
    results = []
    for val in values:
        params = {
            "business_id": business_id,
            "as_of_month": as_of_month,
        }
        
        # Inject the active shock variable
        if variable == "inflow_change_pct":
            params["inflow_change_pct"] = val
        elif variable == "outflow_change_pct":
            params["outflow_change_pct"] = val
        elif variable == "collection_delay_change_days":
            params["collection_delay_change_days"] = val
            
        res = simulate_cashflow_scenario(**params)
        
        results.append({
            "value": val,
            "simulated_cash_inflow": res.simulated.cash_inflow,
            "simulated_net_cash_flow": res.simulated.net_cash_flow,
            "simulated_ending_cash_balance": (res.baseline.cash_inflow + res.baseline.net_cash_flow) + res.simulated.net_cash_flow - res.baseline.cash_inflow, # computed ending balance
            "simulated_repayment_burden_ratio": res.simulated.repayment_burden_ratio,
            "simulated_payroll_burden_ratio": res.simulated.payroll_burden_ratio,
            "simulated_liquidity_gap": res.simulated.liquidity_gap,
            "simulated_risk_score": res.simulated.risk_score,
            "simulated_risk_tier": res.simulated.risk_tier,
            "projected_overdraft_risk": res.simulated.liquidity_gap > 0.0,
            "risk_score_change": res.risk_score_change,
            "risk_tier_change": res.risk_tier_change
        })
        
    return results
