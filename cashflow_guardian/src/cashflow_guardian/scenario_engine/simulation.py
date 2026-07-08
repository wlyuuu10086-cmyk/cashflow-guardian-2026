from typing import Dict, List, Any, Tuple, Optional
import duckdb
from datetime import datetime

import cashflow_guardian.data_engine as de
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk, calculate_rules_based_fallback
from cashflow_guardian.risk_engine.thresholds import map_score_to_tier
from .assumptions import validate_assumptions
from .schemas import ScenarioResult, ScenarioBaseline, ScenarioSimulated

def get_months_prior(month_str: str, n: int) -> str:
    year = int(month_str[:4])
    month = int(month_str[5:7])
    for _ in range(n):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return f"{year:04d}-{month:02d}"

def score_simulated_features(
    business_id: str,
    as_of_month: str,
    sim_features: Dict[str, float]
) -> Tuple[float, str, str, Optional[str]]:
    """Scores a simulated features vector using the cached ML model or fallback."""
    from cashflow_guardian.risk_engine.model_loader import (
        load_risk_models, load_feature_columns, load_model_metadata
    )
    import pandas as pd
    
    best_model = None
    model_meta = None
    feature_cols = None
    
    try:
        _, best_model = load_risk_models()
        model_meta = load_model_metadata()
        feature_cols = load_feature_columns()
    except Exception:
        risk_score = calculate_rules_based_fallback(sim_features)
        _, rag_tier = map_score_to_tier(risk_score)
        return risk_score, rag_tier, "rule_based_fallback", None
        
    try:
        num_cols = feature_cols["numerical_features"]
        
        row_dict = {k: [sim_features.get(k, 0.0)] for k in num_cols}
        
        conn = de.get_readonly_connection()
        cust_row = conn.execute(
            "SELECT industry, region, revenue_band, legal_structure FROM business_customers WHERE business_id = ?",
            (business_id,)
        ).fetchone()
        conn.close()
        
        if not cust_row:
            raise ValueError(f"Business customers record not found for {business_id}")
            
        row_dict["industry"] = [cust_row[0]]
        row_dict["region"] = [cust_row[1]]
        row_dict["revenue_band"] = [cust_row[2]]
        row_dict["legal_structure"] = [cust_row[3]]
        
        X_row = pd.DataFrame(row_dict)
        
        risk_score = float(best_model.predict_proba(X_row)[0, 1])
        _, rag_tier = map_score_to_tier(risk_score)
        
        return risk_score, rag_tier, "ml_model", model_meta.get("selected_model", "RandomForest")
    except Exception:
        risk_score = calculate_rules_based_fallback(sim_features)
        _, rag_tier = map_score_to_tier(risk_score)
        return risk_score, rag_tier, "rule_based_fallback", None

def simulate_cashflow_scenario(
    business_id: str,
    as_of_month: str,
    inflow_change_pct: float = 0.0,
    outflow_change_pct: float = 0.0,
    collection_delay_change_days: float = 0.0,
    payroll_change_pct: float = 0.0,
    debt_service_change_pct: float = 0.0
) -> ScenarioResult:
    """Simulates cash flow what-if scenario by recomputing derived features and scoring them."""
    # 1. Validate inputs
    validate_assumptions(
        inflow_change_pct, outflow_change_pct, collection_delay_change_days,
        payroll_change_pct, debt_service_change_pct
    )
    
    conn = de.get_readonly_connection()
    warnings: List[str] = []
    
    try:
        # Validate ID and Month boundaries
        de.validate_business_id(business_id, conn)
        de.validate_as_of_month(as_of_month, conn)
        
        # 2. Get baseline details
        fv = de.build_point_in_time_features(business_id, as_of_month)
        if not fv.features:
            raise ValueError(f"No snapshot features found for business {business_id} in {as_of_month}")
            
        baseline_risk = score_cashflow_risk(business_id, as_of_month)
        
        # Extract baseline raw variables
        b_inflow = fv.features.get("cash_inflow", 0.0)
        b_outflow = fv.features.get("cash_outflow", 0.0)
        b_net_flow = fv.features.get("net_cash_flow", 0.0)
        b_payroll = fv.features.get("payroll_amount", 0.0)
        b_debt = fv.features.get("scheduled_debt_service", 0.0)
        b_coll_days = fv.features.get("avg_days_to_pay", 0.0)
        b_ending_bal = fv.features.get("ending_cash_balance", 0.0)
        
        # Calculate burden ratios
        b_repay_burden = de.metrics.repayment_burden_ratio(b_debt, b_inflow)
        b_payroll_burden = de.metrics.payroll_burden_ratio(b_payroll, b_inflow)
        b_liquidity_gap = abs(b_ending_bal) if b_ending_bal < 0.0 else 0.0
        
        baseline_obj = ScenarioBaseline(
            cash_inflow=b_inflow,
            cash_outflow=b_outflow,
            net_cash_flow=b_net_flow,
            payroll_amount=b_payroll,
            debt_service=b_debt,
            collection_days=b_coll_days,
            repayment_burden_ratio=b_repay_burden,
            payroll_burden_ratio=b_payroll_burden,
            liquidity_gap=b_liquidity_gap,
            risk_score=baseline_risk["risk_score"],
            risk_tier=baseline_risk["risk_tier"]
        )
        
        # 3. Apply collection delay formula (deferred inflow)
        invoice_row = conn.execute(
            "SELECT invoice_amount_total FROM business_monthly_snapshots WHERE business_id = ? AND month = ?",
            (business_id, as_of_month)
        ).fetchone()
        invoice_amount_total = float(invoice_row[0]) if invoice_row and invoice_row[0] is not None else 0.0
        
        deferred_inflow = 0.0
        if collection_delay_change_days > 0:
            deferred_prop = min(1.0, collection_delay_change_days / 30.0)
            deferred_inflow = invoice_amount_total * deferred_prop
        elif collection_delay_change_days < 0:
            accelerated_prop = min(1.0, abs(collection_delay_change_days) / 30.0)
            deferred_inflow = -invoice_amount_total * accelerated_prop  # Negative means accelerated

            
        coll_delay_details = {
            "formula_used": "deferred_inflow = invoice_amount_total * (collection_delay_change_days / 30.0)",
            "amount_of_inflow_deferred": deferred_inflow,
            "scenario_horizon_days": 30.0,
            "assumptions": f"Linear cash flow impact over a 30-day horizon based on invoice_amount_total of {invoice_amount_total}",
            "limitations": "Assumes uniform invoice distribution and standard 30-day payment cycle."
        }
        
        # 4. Calculate simulated raw values
        sim_inflow = max(0.0, b_inflow * (1.0 + inflow_change_pct / 100.0) - deferred_inflow)
        sim_outflow = max(0.0, b_outflow * (1.0 + outflow_change_pct / 100.0))
        sim_net_flow = sim_inflow - sim_outflow
        sim_payroll = max(0.0, b_payroll * (1.0 + payroll_change_pct / 100.0))
        sim_debt = max(0.0, b_debt * (1.0 + debt_service_change_pct / 100.0))
        sim_coll_days = max(0.0, b_coll_days + collection_delay_change_days)
        
        # Recompute burdens and simulated ending balance
        sim_repay_burden = de.metrics.repayment_burden_ratio(sim_debt, sim_inflow)
        sim_payroll_burden = de.metrics.payroll_burden_ratio(sim_payroll, sim_inflow)
        sim_ending_bal = (b_ending_bal - b_net_flow) + sim_net_flow
        sim_liquidity_gap = abs(sim_ending_bal) if sim_ending_bal < 0.0 else 0.0
        
        # 5. Recompute all affected derived features (Consistency)
        # Fetch history (last 6 months) to recalculate rolling features correctly
        history = de.repository.get_business_history(business_id, as_of_month, months=6)
        snapshots = history.snapshots
        
        # Build lists of historical features up to target month
        hist_inflows = [snap.cash_inflow for snap in snapshots]
        hist_outflows = [snap.cash_outflow for snap in snapshots]
        hist_net_flows = [snap.net_cash_flow for snap in snapshots]
        hist_repay_burdens = [de.metrics.repayment_burden_ratio(snap.scheduled_debt_service, snap.cash_inflow) or 0.0 for snap in snapshots]
        hist_payroll_burdens = [de.metrics.payroll_burden_ratio(snap.payroll_amount, snap.cash_inflow) or 0.0 for snap in snapshots]
        
        # Replace the target month's observed values with simulated values
        if hist_inflows:
            hist_inflows[-1] = sim_inflow
            hist_outflows[-1] = sim_outflow
            hist_net_flows[-1] = sim_net_flow
            hist_repay_burdens[-1] = sim_repay_burden or 0.0
            hist_payroll_burdens[-1] = sim_payroll_burden or 0.0
            
        # Recompute rolling 3-month features
        r3_inflows = hist_inflows[-3:] if len(hist_inflows) >= 3 else hist_inflows
        r3_outflows = hist_outflows[-3:] if len(hist_outflows) >= 3 else hist_outflows
        r3_net_flows = hist_net_flows[-3:] if len(hist_net_flows) >= 3 else hist_net_flows
        r3_repay = hist_repay_burdens[-3:] if len(hist_repay_burdens) >= 3 else hist_repay_burdens
        r3_payroll = hist_payroll_burdens[-3:] if len(hist_payroll_burdens) >= 3 else hist_payroll_burdens
        
        sim_inflow_3m_avg = sum(r3_inflows) / len(r3_inflows) if r3_inflows else 0.0
        sim_outflow_3m_avg = sum(r3_outflows) / len(r3_outflows) if r3_outflows else 0.0
        sim_net_flow_3m_avg = sum(r3_net_flows) / len(r3_net_flows) if r3_net_flows else 0.0
        sim_repay_burden_3m_avg = sum(r3_repay) / len(r3_repay) if r3_repay else 0.0
        sim_payroll_burden_3m_avg = sum(r3_payroll) / len(r3_payroll) if r3_payroll else 0.0
        
        sim_inflow_mom_change = 0.0
        if len(hist_inflows) >= 2:
            sim_inflow_mom_change = hist_inflows[-1] - hist_inflows[-2]
            
        # Volatility recalculation over 6 months
        sim_volatility = de.metrics.cash_flow_volatility(hist_net_flows) or 0.0
        
        # Build simulated features dict
        sim_features = fv.features.copy()
        sim_features["cash_inflow"] = sim_inflow
        sim_features["cash_outflow"] = sim_outflow
        sim_features["net_cash_flow"] = sim_net_flow
        sim_features["payroll_amount"] = sim_payroll
        sim_features["scheduled_debt_service"] = sim_debt
        sim_features["avg_days_to_pay"] = sim_coll_days
        sim_features["ending_cash_balance"] = sim_ending_bal
        sim_features["cash_inflow_3m_avg"] = sim_inflow_3m_avg
        sim_features["cash_outflow_3m_avg"] = sim_outflow_3m_avg
        sim_features["net_cash_flow_3m_avg"] = sim_net_flow_3m_avg
        sim_features["net_cash_flow_6m_volatility"] = sim_volatility
        sim_features["cash_inflow_mom_change"] = sim_inflow_mom_change
        sim_features["repayment_burden_3m_avg"] = sim_repay_burden_3m_avg
        sim_features["payroll_burden_3m_avg"] = sim_payroll_burden_3m_avg
        
        # 6. Score the simulated features
        sim_score, sim_tier, scoring_mode, model_version = score_simulated_features(
            business_id, as_of_month, sim_features
        )
        
        simulated_obj = ScenarioSimulated(
            cash_inflow=sim_inflow,
            cash_outflow=sim_outflow,
            net_cash_flow=sim_net_flow,
            payroll_amount=sim_payroll,
            debt_service=sim_debt,
            collection_days=sim_coll_days,
            repayment_burden_ratio=sim_repay_burden,
            payroll_burden_ratio=sim_payroll_burden,
            liquidity_gap=sim_liquidity_gap,
            risk_score=sim_score,
            risk_tier=sim_tier
        )
        
        # Calculate tier change description
        b_tier = baseline_risk["risk_tier"]
        tier_map = {"GREEN": 1, "AMBER": 2, "RED": 3, "CRITICAL": 4}
        b_val = tier_map.get(b_tier, 0)
        s_val = tier_map.get(sim_tier, 0)
        
        if s_val > b_val:
            tier_change = "deteriorated"
        elif s_val < b_val:
            tier_change = "improved"
        else:
            tier_change = "no_change"
            
        result = ScenarioResult(
            business_id=business_id,
            as_of_month=as_of_month,
            assumptions={
                "inflow_change_pct": inflow_change_pct,
                "outflow_change_pct": outflow_change_pct,
                "collection_delay_change_days": collection_delay_change_days,
                "payroll_change_pct": payroll_change_pct,
                "debt_service_change_pct": debt_service_change_pct
            },
            baseline=baseline_obj,
            simulated=simulated_obj,
            risk_score_change=float(sim_score - baseline_risk["risk_score"]),
            risk_tier_change=tier_change,
            scoring_mode=scoring_mode,
            model_version=model_version,
            warnings=warnings + [f"Simulated risk score {sim_score:.4f} is a model projection under hypothetical shock assumptions, not an observed future outcome."],
            future_data_used=False,
            collection_delay_details=coll_delay_details
        )
        
        return result
        
    finally:
        conn.close()
