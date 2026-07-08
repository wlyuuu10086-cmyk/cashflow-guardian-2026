import duckdb
from typing import List, Dict, Any, Optional
from .connection import get_readonly_connection
from .schemas import FeatureVectorResult, ProvenanceMetadata
from .provenance import build_provenance
from .quality import check_business_data_quality
from .repository import get_peer_benchmark
from .validators import validate_business_id, validate_as_of_month, ValidationError
from .metrics import (
    net_cash_flow, repayment_burden_ratio, payroll_burden_ratio,
    cash_flow_volatility, percentage_change, rolling_mean,
    consecutive_negative_cash_flow_months, benchmark_absolute_gap,
    benchmark_percentage_gap
)

def build_point_in_time_features(business_id: str, as_of_month: str) -> FeatureVectorResult:
    """Builds a point-in-time feature vector using only data up to as_of_month."""
    warnings: List[str] = []
    
    # 1. Run Data Quality Check first
    dq = check_business_data_quality(business_id, as_of_month)
    if not dq.can_build_features:
        # Failure behavior: Return empty feature vector with warnings
        prov = dq.provenance or build_provenance(
            source_tables=["business_monthly_snapshots"],
            as_of_month=as_of_month,
            row_count=0,
            warnings=dq.errors + dq.warnings
        )
        return FeatureVectorResult(
            business_id=business_id,
            month=as_of_month,
            features={},
            feature_names=[],
            missing_feature_warnings=dq.errors + dq.warnings,
            provenance=prov,
            future_data_used=False
        )
        
    conn = get_readonly_connection()
    try:
        # Fetch snapshots up to 6 months back for rolling features
        cursor = conn.execute(
            """
            SELECT 
                month,
                opening_cash_balance_proxy,
                ending_cash_balance_proxy,
                avg_daily_balance_proxy,
                overdraft_days_proxy,
                transaction_count,
                cash_inflow_observed,
                cash_outflow_observed,
                net_cash_flow_observed,
                invoice_count,
                invoice_amount_total,
                avg_days_to_pay,
                late_invoice_rate,
                payroll_amount,
                employee_count,
                scheduled_debt_service,
                actual_debt_service,
                max_dpd,
                available_credit_drawn_ratio
            FROM business_monthly_snapshots
            WHERE business_id = ? AND month <= ?
            ORDER BY month DESC
            LIMIT 6
            """,
            (business_id, as_of_month)
        )
        rows = cursor.fetchall()
        
        # Build column index
        col_names = [desc[0] for desc in cursor.description]
        col_idx = {name: i for i, name in enumerate(col_names)}
        
        # Rows are sorted descending (newest first). Let's reverse to ascending (chronological)
        rows.reverse()
        n_rows = len(rows)
        
        # Get target/current month (the last row)
        curr = rows[-1]
        
        # Extract current month attributes
        c_inflow = curr[col_idx["cash_inflow_observed"]] or 0.0
        c_outflow = curr[col_idx["cash_outflow_observed"]] or 0.0
        c_net_flow = curr[col_idx["net_cash_flow_observed"]] or 0.0
        c_ending_bal = curr[col_idx["ending_cash_balance_proxy"]] or 0.0
        c_avg_daily_bal = curr[col_idx["avg_daily_balance_proxy"]] or 0.0
        c_overdraft_days = int(curr[col_idx["overdraft_days_proxy"]] or 0)
        c_late_inv_rate = curr[col_idx["late_invoice_rate"]] or 0.0
        c_avg_days_to_pay = curr[col_idx["avg_days_to_pay"]] or 0.0
        c_payroll_amount = curr[col_idx["payroll_amount"]] or 0.0
        c_sched_debt = curr[col_idx["scheduled_debt_service"]] or 0.0
        c_act_debt = curr[col_idx["actual_debt_service"]] or 0.0
        c_max_dpd = int(curr[col_idx["max_dpd"]] or 0)
        c_drawn_ratio = curr[col_idx["available_credit_drawn_ratio"]] or 0.0
        
        # Calculate rolling 3-month features (using rows -3 to -1)
        r3 = rows[-3:] if n_rows >= 3 else rows
        
        r3_inflow = [row[col_idx["cash_inflow_observed"]] for row in r3]
        r3_outflow = [row[col_idx["cash_outflow_observed"]] for row in r3]
        r3_net_flow = [row[col_idx["net_cash_flow_observed"]] for row in r3]
        r3_overdraft = [row[col_idx["overdraft_days_proxy"]] for row in r3]
        r3_late_inv = [row[col_idx["late_invoice_rate"]] for row in r3]
        
        # Repayment burden lists
        r3_repay_burden = []
        for row in r3:
            inf = row[col_idx["cash_inflow_observed"]]
            sched = row[col_idx["scheduled_debt_service"]]
            r3_repay_burden.append(repayment_burden_ratio(sched, inf))
            
        r3_payroll_burden = []
        for row in r3:
            inf = row[col_idx["cash_inflow_observed"]]
            pay = row[col_idx["payroll_amount"]]
            r3_payroll_burden.append(payroll_burden_ratio(pay, inf))
            
        cash_inflow_3m_avg = rolling_mean(r3_inflow) or 0.0
        cash_outflow_3m_avg = rolling_mean(r3_outflow) or 0.0
        net_cash_flow_3m_avg = rolling_mean(r3_net_flow) or 0.0
        
        # Net cash flow volatility (sample std dev)
        # Note: Volatility requires standard deviation. We will calculate both 3-month and 6-month
        net_cash_flow_3m_volatility = cash_flow_volatility(r3_net_flow) or 0.0
        
        r6_net_flow = [row[col_idx["net_cash_flow_observed"]] for row in rows]
        net_cash_flow_6m_volatility = cash_flow_volatility(r6_net_flow) or 0.0
        
        repayment_burden_3m_avg = rolling_mean(r3_repay_burden) or 0.0
        payroll_burden_3m_avg = rolling_mean(r3_payroll_burden) or 0.0
        overdraft_days_3m_sum = sum([int(x or 0) for x in r3_overdraft])
        late_invoice_rate_3m_avg = rolling_mean(r3_late_inv) or 0.0
        
        # MoM change (current vs t-1)
        cash_inflow_mom_change = 0.0
        if n_rows >= 2:
            prev = rows[-2]
            prev_inflow = prev[col_idx["cash_inflow_observed"]] or 0.0
            cash_inflow_mom_change = c_inflow - prev_inflow
            
        # 3-month change (current vs t-3)
        cash_inflow_3m_change = 0.0
        collection_days_3m_change = 0.0
        repayment_burden_3m_change = 0.0
        
        if n_rows >= 4:
            t3 = rows[-4]
            t3_inflow = t3[col_idx["cash_inflow_observed"]] or 0.0
            t3_avg_days = t3[col_idx["avg_days_to_pay"]] or 0.0
            t3_sched_debt = t3[col_idx["scheduled_debt_service"]] or 0.0
            
            t3_burden = repayment_burden_ratio(t3_sched_debt, t3_inflow) or 0.0
            curr_burden = repayment_burden_ratio(c_sched_debt, c_inflow) or 0.0
            
            cash_inflow_3m_change = c_inflow - t3_inflow
            collection_days_3m_change = c_avg_days_to_pay - t3_avg_days
            repayment_burden_3m_change = curr_burden - t3_burden
            
        # Consecutive negative cash flow months (looking at whole history up to 6 months)
        all_net_flows = [row[col_idx["net_cash_flow_observed"]] for row in rows]
        consec_neg_months = consecutive_negative_cash_flow_months(all_net_flows)
        
        # Industry benchmark gaps
        peer = get_peer_benchmark(business_id, as_of_month)
        industry_margin_gap = peer.deviations.get("margin_delta", 0.0)
        industry_volatility_ratio = peer.deviations.get("volatility_ratio", 0.0)
        industry_collection_days_gap = peer.deviations.get("collection_days_delta", 0.0)
        
        # Compile all features into dictionary
        features = {
            "cash_inflow": c_inflow,
            "cash_outflow": c_outflow,
            "net_cash_flow": c_net_flow,
            "ending_cash_balance": c_ending_bal,
            "avg_daily_balance": c_avg_daily_bal,
            "overdraft_days": c_overdraft_days,
            "late_invoice_rate": c_late_inv_rate,
            "avg_days_to_pay": c_avg_days_to_pay,
            "payroll_amount": c_payroll_amount,
            "scheduled_debt_service": c_sched_debt,
            "actual_debt_service": c_act_debt,
            "max_dpd": c_max_dpd,
            "available_credit_drawn_ratio": c_drawn_ratio,
            "cash_inflow_3m_avg": cash_inflow_3m_avg,
            "cash_outflow_3m_avg": cash_outflow_3m_avg,
            "net_cash_flow_3m_avg": net_cash_flow_3m_avg,
            "net_cash_flow_3m_volatility": net_cash_flow_3m_volatility,
            "net_cash_flow_6m_volatility": net_cash_flow_6m_volatility,
            "cash_inflow_mom_change": cash_inflow_mom_change,
            "cash_inflow_3m_change": cash_inflow_3m_change,
            "collection_days_3m_change": collection_days_3m_change,
            "repayment_burden_3m_change": repayment_burden_3m_change,
            "repayment_burden_3m_avg": repayment_burden_3m_avg,
            "payroll_burden_3m_avg": payroll_burden_3m_avg,
            "overdraft_days_3m_sum": overdraft_days_3m_sum,
            "late_invoice_rate_3m_avg": late_invoice_rate_3m_avg,
            "consecutive_negative_cash_flow_months": consec_neg_months,
            "industry_margin_gap": industry_margin_gap,
            "industry_volatility_ratio": industry_volatility_ratio,
            "industry_collection_days_gap": industry_collection_days_gap
        }
        
        feature_names = list(features.keys())
        
        prov = build_provenance(
            source_tables=["business_monthly_snapshots", "business_customers", "industry_benchmark"],
            as_of_month=as_of_month,
            row_count=1,
            warnings=warnings
        )
        
        return FeatureVectorResult(
            business_id=business_id,
            month=as_of_month,
            features=features,
            feature_names=feature_names,
            missing_feature_warnings=warnings,
            provenance=prov,
            future_data_used=False
        )
        
    finally:
        conn.close()
