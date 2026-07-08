import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import duckdb

import cashflow_guardian.data_engine as de
from .schemas import (
    BusinessBenchmarkResult, PeerGroupDefinition,
    BenchmarkMetricComparison, BenchmarkProvenance
)
from .peer_groups import determine_peer_group

def get_months_prior(month_str: str, n: int) -> str:
    """Calculates n months prior to YYYY-MM."""
    year = int(month_str[:4])
    month = int(month_str[5:7])
    for _ in range(n):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return f"{year:04d}-{month:02d}"

def calculate_percentile_rank(peer_values: List[float], business_value: float, lower_is_better: bool = True) -> float:
    """Calculates percentile rank of the business value compared to peers.
    
    The target business is excluded from the peer population (which is passed in).
    Formula: (count of peers with value <= business_value) / total_peers * 100
    """
    if not peer_values:
        return 0.0
    valid_peers = [v for v in peer_values if v is not None]
    if not valid_peers:
        return 0.0
        
    count = sum(1 for v in valid_peers if v <= business_value)
    return float(round((count / len(valid_peers)) * 100.0, 2))

def determine_comparison_direction(
    business_value: Optional[float],
    peer_value: Optional[float],
    metric_name: str
) -> Tuple[str, str]:
    """Determines direction (better, similar, worse, unavailable) and interpretation code.
    
    Uses deterministic tolerances for each metric.
    """
    if business_value is None or peer_value is None:
        return "unavailable", "METRIC_UNAVAILABLE"
        
    diff = business_value - peer_value
    
    if metric_name == "volatility":
        # Lower is better. Tolerance +/- 15% of peer_value
        tol = abs(peer_value) * 0.15
        if diff > tol:
            return "worse", "HIGH_VOLATILITY"
        elif diff < -tol:
            return "better", "STABLE_CASH_FLOW"
        else:
            return "similar", "NORMAL_VOLATILITY"
            
    elif metric_name == "collection_days":
        # Lower is better. Tolerance +/- 5 days
        tol = 5.0
        if diff > tol:
            return "worse", "SLOW_COLLECTION"
        elif diff < -tol:
            return "better", "FAST_COLLECTION"
        else:
            return "similar", "NORMAL_COLLECTION"
            
    elif metric_name == "late_invoice_rate":
        # Lower is better. Tolerance +/- 0.10 (10%)
        tol = 0.10
        if diff > tol:
            return "worse", "HIGH_LATE_INVOICES"
        elif diff < -tol:
            return "better", "LOW_LATE_INVOICES"
        else:
            return "similar", "NORMAL_LATE_INVOICES"
            
    elif metric_name == "repayment_burden":
        # Lower is better. Tolerance +/- 0.05
        tol = 0.05
        if diff > tol:
            return "worse", "HIGH_DEBT_BURDEN"
        elif diff < -tol:
            return "better", "LOW_DEBT_BURDEN"
        else:
            return "similar", "NORMAL_DEBT_BURDEN"
            
    elif metric_name == "payroll_burden":
        # Lower is better. Tolerance +/- 0.10
        tol = 0.10
        if diff > tol:
            return "worse", "HIGH_PAYROLL_BURDEN"
        elif diff < -tol:
            return "better", "LOW_PAYROLL_BURDEN"
        else:
            return "similar", "NORMAL_PAYROLL_BURDEN"
            
    elif metric_name == "credit_utilization":
        # Lower is better. Tolerance +/- 0.15
        tol = 0.15
        if diff > tol:
            return "worse", "HIGH_UTILIZATION"
        elif diff < -tol:
            return "better", "LOW_UTILIZATION"
        else:
            return "similar", "NORMAL_UTILIZATION"
            
    elif metric_name == "overdraft_days":
        # Lower is better. Tolerance +/- 1 day
        tol = 1.0
        if diff > tol:
            return "worse", "HIGH_OVERDRAFT_DAYS"
        elif business_value == 0 and peer_value > 0:
            return "better", "NO_OVERDRAFT"
        else:
            return "similar", "NORMAL_OVERDRAFT"
            
    elif metric_name == "trend":
        # Higher is better. Tolerance +/- 1000.0
        tol = 1000.0
        if diff < -tol:
            return "worse", "DECLINING_CASH_FLOW"
        elif diff > tol:
            return "better", "GROWING_CASH_FLOW"
        else:
            return "similar", "STABLE_TREND"
            
    return "unavailable", "UNKNOWN_METRIC"

def compare_business_with_peers(
    business_id: str,
    as_of_month: str,
    min_peer_count: int = 5
) -> BusinessBenchmarkResult:
    """Performs deterministic benchmarking for a business ID against its peer group."""
    conn = de.get_readonly_connection()
    warnings: List[str] = []
    
    try:
        # Validate input boundaries
        de.validate_business_id(business_id, conn)
        de.validate_as_of_month(as_of_month, conn)
        
        # 1. Determine Peer Group (excluding target business)
        method, industry, revenue_band, peer_ids = determine_peer_group(
            business_id, as_of_month, conn, min_peer_count
        )
        
        peer_group_def = PeerGroupDefinition(
            method=method,
            industry=industry,
            revenue_band=revenue_band,
            peer_count=len(peer_ids)
        )
        
        # 2. Fetch target business values
        # Get target business features using build_point_in_time_features
        fv = de.build_point_in_time_features(business_id, as_of_month)
        
        # Calculate target business 3-month net cash flow trend explicitly
        target_trend = None
        trend_row = conn.execute(
            """
            SELECT 
                (SELECT net_cash_flow_observed FROM business_monthly_snapshots WHERE business_id = ? AND month = ?) -
                (SELECT net_cash_flow_observed FROM business_monthly_snapshots WHERE business_id = ? AND month = ?)
            """,
            (business_id, as_of_month, business_id, get_months_prior(as_of_month, 2))
        ).fetchone()
        if trend_row and trend_row[0] is not None:
            target_trend = float(trend_row[0])
            
        target_metrics = {
            "volatility": fv.features.get("net_cash_flow_6m_volatility"),
            "collection_days": fv.features.get("avg_days_to_pay"),
            "late_invoice_rate": fv.features.get("late_invoice_rate"),
            "repayment_burden": de.metrics.repayment_burden_ratio(
                fv.features.get("scheduled_debt_service"), fv.features.get("cash_inflow")
            ),
            "payroll_burden": de.metrics.payroll_burden_ratio(
                fv.features.get("payroll_amount"), fv.features.get("cash_inflow")
            ),
            "credit_utilization": fv.features.get("available_credit_drawn_ratio"),
            "overdraft_days": float(fv.features.get("overdraft_days", 0.0)) if fv.features.get("overdraft_days") is not None else None,
            "trend": target_trend
        }
        
        peer_medians: Dict[str, Optional[float]] = {}
        peer_distributions: Dict[str, List[float]] = {}
        source_prov = "observed_data"
        
        if method == "industry_benchmark_table":
            # Final Fallback: official benchmarks from industry_benchmark table
            source_prov = "benchmark_table"
            warnings.append(f"Insufficient peer group data (required >= {min_peer_count}). Falling back to industry benchmark reference table.")
            
            bench_row = conn.execute(
                "SELECT benchmark_margin, benchmark_cash_flow_volatility, benchmark_collection_days, benchmark_repayment_burden_pct, payroll_intensity "
                "FROM industry_benchmark WHERE industry = ?",
                (industry,)
            ).fetchone()
            
            if not bench_row:
                raise ValueError(f"Industry benchmark not found for industry {industry}")
                
            peer_medians["volatility"] = float(bench_row[1]) if bench_row[1] is not None else None
            peer_medians["collection_days"] = float(bench_row[2]) if bench_row[2] is not None else None
            peer_medians["late_invoice_rate"] = None # Not available in industry_benchmark table
            peer_medians["repayment_burden"] = float(bench_row[3]) / 100.0 if bench_row[3] is not None else None
            peer_medians["payroll_burden"] = float(bench_row[4]) if bench_row[4] is not None else None
            peer_medians["credit_utilization"] = None
            peer_medians["overdraft_days"] = None
            peer_medians["trend"] = None
            
        else:
            # Query actual peers
            # 2.1 Get current month values
            peer_data_rows = conn.execute(
                f"""
                SELECT 
                    business_id,
                    avg_days_to_pay,
                    late_invoice_rate,
                    available_credit_drawn_ratio,
                    overdraft_days_proxy,
                    (scheduled_debt_service / NULLIF(cash_inflow_observed, 0.0)) as repayment_burden,
                    (payroll_amount / NULLIF(cash_inflow_observed, 0.0)) as payroll_burden
                FROM business_monthly_snapshots
                WHERE business_id IN ({','.join(['?']*len(peer_ids))}) AND month = ?
                """,
                peer_ids + [as_of_month]
            ).fetchall()
            
            peer_dict = {
                r[0]: {
                    "collection_days": r[1],
                    "late_invoice_rate": r[2],
                    "credit_utilization": r[3],
                    "overdraft_days": float(r[4]) if r[4] is not None else None,
                    "repayment_burden": r[5],
                    "payroll_burden": r[6]
                }
                for r in peer_data_rows
            }
            
            # 2.2 Get 6m net cash flow volatility for peers
            start_vol_month = get_months_prior(as_of_month, 5)
            peer_vol_rows = conn.execute(
                f"""
                SELECT business_id, stddev_samp(net_cash_flow_observed) as vol
                FROM business_monthly_snapshots
                WHERE business_id IN ({','.join(['?']*len(peer_ids))}) AND month >= ? AND month <= ?
                GROUP BY business_id
                """,
                peer_ids + [start_vol_month, as_of_month]
            ).fetchall()
            
            for bid, vol in peer_vol_rows:
                if bid in peer_dict:
                    peer_dict[bid]["volatility"] = vol
                    
            # 2.3 Get 3m trend for peers
            t2_month = get_months_prior(as_of_month, 2)
            peer_trend_rows = conn.execute(
                f"""
                WITH peer_t AS (
                    SELECT business_id, net_cash_flow_observed as net_t
                    FROM business_monthly_snapshots
                    WHERE business_id IN ({','.join(['?']*len(peer_ids))}) AND month = ?
                ),
                peer_t2 AS (
                    SELECT business_id, net_cash_flow_observed as net_t2
                    FROM business_monthly_snapshots
                    WHERE business_id IN ({','.join(['?']*len(peer_ids))}) AND month = ?
                )
                SELECT t.business_id, (t.net_t - COALESCE(t2.net_t2, 0.0)) as trend
                FROM peer_t t
                LEFT JOIN peer_t2 t2 ON t.business_id = t2.business_id
                """,
                peer_ids + [as_of_month] + peer_ids + [t2_month]
            ).fetchall()
            
            for bid, trend in peer_trend_rows:
                if bid in peer_dict:
                    peer_dict[bid]["trend"] = trend
                    
            # 2.4 Compile distributions and calculate medians
            metrics_keys = ["volatility", "collection_days", "late_invoice_rate", "repayment_burden", "payroll_burden", "credit_utilization", "overdraft_days", "trend"]
            for k in metrics_keys:
                vals = [peer_dict[bid].get(k) for bid in peer_ids if bid in peer_dict and peer_dict[bid].get(k) is not None]
                peer_distributions[k] = vals
                if vals:
                    peer_medians[k] = float(np.median(vals))
                else:
                    peer_medians[k] = None
                    
        # 3. Calculate gaps, ranks, and directions
        metric_comparisons = {}
        for k in ["volatility", "collection_days", "late_invoice_rate", "repayment_burden", "payroll_burden", "credit_utilization", "overdraft_days", "trend"]:
            b_val = target_metrics.get(k)
            p_val = peer_medians.get(k)
            
            abs_gap = None
            pct_gap = None
            if b_val is not None and p_val is not None:
                abs_gap = float(b_val - p_val)
                if p_val != 0.0:
                    pct_gap = float((b_val - p_val) / abs(p_val))
                    
            p_rank = None
            if method != "industry_benchmark_table" and b_val is not None:
                p_rank = calculate_percentile_rank(peer_distributions.get(k, []), b_val)
                
            dir_val, interp_val = determine_comparison_direction(b_val, p_val, k)
            
            # Handle metric unavailable warnings
            if dir_val == "unavailable":
                warnings.append(f"Metric '{k}' comparison is unavailable (missing target or peer benchmark values).")
                
            metric_comparisons[k] = BenchmarkMetricComparison(
                metric_name=k,
                business_value=float(b_val) if b_val is not None else None,
                peer_value=float(p_val) if p_val is not None else None,
                absolute_gap=abs_gap,
                percentage_gap=pct_gap,
                percentile_rank=p_rank,
                direction=dir_val,
                interpretation_code=interp_val,
                source_provenance=source_prov
            )
            
        prov = BenchmarkProvenance(
            source_tables=["business_monthly_snapshots", "business_customers", "industry_benchmark"],
            as_of_month=as_of_month,
            query_timestamp=datetime.utcnow().isoformat() + "Z",
            future_data_used=False,
            warnings=warnings
        )
        
        return BusinessBenchmarkResult(
            business_id=business_id,
            as_of_month=as_of_month,
            peer_group=peer_group_def,
            metrics=metric_comparisons,
            provenance=prov,
            warnings=warnings
        )
        
    finally:
        conn.close()
