import duckdb
from typing import List, Optional, Dict, Any
from .connection import get_readonly_connection
from .schemas import (
    BusinessHistoryResult, BusinessMonthlyMetric, PortfolioSnapshotResult,
    PortfolioBusinessRecord, PeerBenchmarkResult, ProvenanceMetadata
)
from .provenance import build_provenance
from .validators import (
    validate_business_id, validate_as_of_month, validate_history_length, ValidationError
)
from .queries import (
    GET_BUSINESS_HISTORY_QUERY, GET_PORTFOLIO_SNAPSHOT_QUERY,
    GET_BUSINESS_PEER_INFO_QUERY, GET_INDUSTRY_BENCHMARK_QUERY
)
from .metrics import (
    net_cash_flow, repayment_burden_ratio, cash_flow_volatility,
    benchmark_absolute_gap, benchmark_percentage_gap
)

def get_business_history(business_id: str, as_of_month: str, months: int = 6) -> BusinessHistoryResult:
    """Retrieves historical snapshots for a specific business up to the selected as-of month.
    
    If fewer than the requested months are available, returns what is available plus a warning.
    """
    conn = get_readonly_connection()
    warnings: List[str] = []
    
    try:
        # Validate inputs
        validate_business_id(business_id, conn)
        validate_as_of_month(as_of_month, conn)
        validate_history_length(months)
        
        # Execute parameterized query
        cursor = conn.execute(GET_BUSINESS_HISTORY_QUERY, (business_id, as_of_month, months))
        rows = cursor.fetchall()
        
        col_names = [desc[0] for desc in cursor.description]
        col_idx = {name: i for i, name in enumerate(col_names)}
        
        snapshots: List[BusinessMonthlyMetric] = []
        # The query returns rows in descending order (newest first).
        # We process them and then reverse so the list goes ascending (chronological).
        for row in rows:
            snapshots.append(
                BusinessMonthlyMetric(
                    month=row[col_idx["month"]],
                    cash_inflow=row[col_idx["cash_inflow"]] or 0.0,
                    cash_outflow=row[col_idx["cash_outflow"]] or 0.0,
                    net_cash_flow=row[col_idx["net_cash_flow"]] or 0.0,
                    ending_balance=row[col_idx["ending_balance"]] or 0.0,
                    average_daily_balance=row[col_idx["average_daily_balance"]] or 0.0,
                    overdraft_days=int(row[col_idx["overdraft_days"]] or 0),
                    invoice_count=int(row[col_idx["invoice_count"]] or 0),
                    average_days_to_pay=row[col_idx["avg_days_to_pay"]] or 0.0,
                    late_invoice_rate=row[col_idx["late_invoice_rate"]] or 0.0,
                    payroll_amount=row[col_idx["payroll_amount"]] or 0.0,
                    employee_count=int(row[col_idx["employee_count"]] or 0),
                    scheduled_debt_service=row[col_idx["scheduled_debt_service"]] or 0.0,
                    actual_debt_service=row[col_idx["actual_debt_service"]] or 0.0,
                    maximum_days_past_due=int(row[col_idx["maximum_days_past_due"]] or 0),
                    credit_utilization_ratio=row[col_idx["credit_utilization_ratio"]] or 0.0
                )
            )
            
        snapshots.reverse()
        
        # Add warning if fewer months than requested are available
        if len(snapshots) < months:
            warnings.append(
                f"Requested {months} months of history, but only {len(snapshots)} months were available "
                f"prior to and including {as_of_month}."
            )
            
        prov = build_provenance(
            source_tables=["business_monthly_snapshots"],
            as_of_month=as_of_month,
            row_count=len(snapshots),
            warnings=warnings
        )
        
        return BusinessHistoryResult(
            business_id=business_id,
            history_months=len(snapshots),
            snapshots=snapshots,
            provenance=prov
        )
        
    finally:
        conn.close()

def get_portfolio_snapshot(
    as_of_month: str, 
    industry: Optional[str] = None, 
    region: Optional[str] = None, 
    limit: int = 1500
) -> PortfolioSnapshotResult:
    """Retrieves point-in-time metrics and data quality status for all SMEs for a target month."""
    conn = get_readonly_connection()
    warnings: List[str] = []
    
    try:
        # Validate month
        validate_as_of_month(as_of_month, conn)
        
        # Build query dynamically based on optional filters
        query = GET_PORTFOLIO_SNAPSHOT_QUERY
        params: List[Any] = [as_of_month]
        
        if industry:
            query += " AND c.industry = ?"
            params.append(industry)
        if region:
            query += " AND c.region = ?"
            params.append(region)
            
        query += " ORDER BY c.business_id LIMIT ?"
        params.append(limit)
        
        # Pre-query history counts in bulk to check data quality status efficiently
        hist_cursor = conn.execute(
            """
            SELECT business_id, COUNT(*) 
            FROM business_monthly_snapshots 
            WHERE month <= ? 
            GROUP BY business_id
            """,
            (as_of_month,)
        )
        history_counts = {row[0]: row[1] for row in hist_cursor.fetchall()}
        
        # Execute query
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        col_names = [desc[0] for desc in cursor.description]
        col_idx = {name: i for i, name in enumerate(col_names)}
        
        records: List[PortfolioBusinessRecord] = []
        for row in rows:
            bid = row[col_idx["business_id"]]
            hist_len = history_counts.get(bid, 0)
            
            # Simple data quality status determination
            dq_status = "COMPLETED"
            if row[col_idx["ending_cash_balance"]] is None or row[col_idx["cash_inflow"]] is None:
                dq_status = "BLOCKED"
            elif hist_len < 3:
                dq_status = "WARNING"
                
            records.append(
                PortfolioBusinessRecord(
                    business_id=bid,
                    business_name=row[col_idx["business_name"]],
                    industry=row[col_idx["industry"]],
                    region=row[col_idx["region"]],
                    revenue_band=row[col_idx["revenue_band"]],
                    relationship_manager_id=row[col_idx["relationship_manager_id"]],
                    cash_inflow=row[col_idx["cash_inflow"]] or 0.0,
                    cash_outflow=row[col_idx["cash_outflow"]] or 0.0,
                    net_cash_flow=row[col_idx["net_cash_flow"]] or 0.0,
                    ending_cash_balance=row[col_idx["ending_cash_balance"]] or 0.0,
                    average_collection_days=row[col_idx["average_collection_days"]] or 0.0,
                    late_invoice_rate=row[col_idx["late_invoice_rate"]] or 0.0,
                    payroll_amount=row[col_idx["payroll_amount"]] or 0.0,
                    scheduled_debt_service=row[col_idx["scheduled_debt_service"]] or 0.0,
                    maximum_days_past_due=int(row[col_idx["maximum_days_past_due"]] or 0),
                    credit_utilization_ratio=row[col_idx["credit_utilization_ratio"]] or 0.0,
                    data_quality_status=dq_status
                )
            )
            
        prov = build_provenance(
            source_tables=["business_monthly_snapshots", "business_customers"],
            as_of_month=as_of_month,
            row_count=len(records),
            warnings=warnings
        )
        
        return PortfolioSnapshotResult(
            as_of_month=as_of_month,
            records=records,
            provenance=prov
        )
        
    finally:
        conn.close()

def get_peer_benchmark(business_id: str, as_of_month: str) -> PeerBenchmarkResult:
    """Benchmarks a business's cash flow features against its industry segment benchmarks."""
    conn = get_readonly_connection()
    warnings: List[str] = []
    
    try:
        # Validate ID and month
        validate_business_id(business_id, conn)
        validate_as_of_month(as_of_month, conn)
        
        # 1. Fetch business industry details
        peer_info = conn.execute(GET_BUSINESS_PEER_INFO_QUERY, (business_id,)).fetchone()
        if not peer_info:
            raise ValidationError(f"Business details not found for business {business_id}")
        industry_name, industry_id = peer_info
        
        # 2. Fetch industry benchmarks
        benchmark_row = conn.execute(GET_INDUSTRY_BENCHMARK_QUERY, (industry_id,)).fetchone()
        if not benchmark_row:
            raise ValidationError(f"Benchmark details not found for industry {industry_name} ({industry_id})")
            
        # Parse benchmark columns
        benchmark_margin = float(benchmark_row[2] or 0.0)
        benchmark_vol = float(benchmark_row[3] or 0.0)
        benchmark_coll_days = float(benchmark_row[4] or 0.0)
        benchmark_repay_pct = float(benchmark_row[5] or 0.0)
        
        # 3. Retrieve business observed features
        # We need historical net cash flows to calculate volatility over last 6 months
        vol_cursor = conn.execute(
            """
            SELECT net_cash_flow_observed 
            FROM business_monthly_snapshots 
            WHERE business_id = ? AND month <= ? 
            ORDER BY month DESC 
            LIMIT 6
            """,
            (business_id, as_of_month)
        )
        vol_rows = vol_cursor.fetchall()
        net_flows = [row[0] for row in vol_rows]
        vol_val = cash_flow_volatility(net_flows)
        
        # Retrieve target month snapshot for margin, collection days, repayment burden
        snap_row = conn.execute(
            """
            SELECT 
                cash_inflow_observed,
                net_cash_flow_observed,
                avg_days_to_pay,
                scheduled_debt_service
            FROM business_monthly_snapshots
            WHERE business_id = ? AND month = ?
            """,
            (business_id, as_of_month)
        ).fetchone()
        
        current_margin = None
        avg_collection_days = None
        repayment_burden_pct = None
        
        if snap_row:
            inflow = snap_row[0]
            net_flow = snap_row[1]
            avg_days = snap_row[2]
            sched_debt = snap_row[3]
            
            # margin = net_cash_flow / inflow
            if inflow is not None and inflow > 0.0:
                current_margin = (net_flow or 0.0) / inflow
                repayment_burden_pct = ((sched_debt or 0.0) / inflow) * 100.0
            else:
                current_margin = 0.0
                repayment_burden_pct = 0.0
                
            avg_collection_days = avg_days or 0.0
            
        # 4. Calculate deviations
        margin_delta = None
        volatility_ratio = None
        collection_days_delta = None
        
        if current_margin is not None:
            margin_delta = current_margin - benchmark_margin
        if vol_val is not None:
            volatility_ratio = (vol_val / benchmark_vol) if benchmark_vol > 0.0 else 0.0
        if avg_collection_days is not None:
            collection_days_delta = avg_collection_days - benchmark_coll_days
            
        peer_metrics = {
            "benchmark_margin": benchmark_margin,
            "benchmark_cash_flow_volatility": benchmark_vol,
            "benchmark_collection_days": benchmark_coll_days,
            "benchmark_repayment_burden_pct": benchmark_repay_pct
        }
        
        business_metrics = {
            "current_margin": current_margin if current_margin is not None else 0.0,
            "cash_flow_volatility": vol_val if vol_val is not None else 0.0,
            "avg_collection_days": avg_collection_days if avg_collection_days is not None else 0.0,
            "repayment_burden_pct": repayment_burden_pct if repayment_burden_pct is not None else 0.0
        }
        
        deviations = {
            "margin_delta": margin_delta if margin_delta is not None else 0.0,
            "volatility_ratio": volatility_ratio if volatility_ratio is not None else 0.0,
            "collection_days_delta": collection_days_delta if collection_days_delta is not None else 0.0
        }
        
        prov = build_provenance(
            source_tables=["industry_benchmark", "business_customers", "business_monthly_snapshots"],
            as_of_month=as_of_month,
            row_count=1,
            warnings=warnings
        )
        
        return PeerBenchmarkResult(
            business_id=business_id,
            industry=industry_name,
            peer_metrics=peer_metrics,
            business_metrics=business_metrics,
            deviations=deviations,
            provenance=prov
        )
        
    finally:
        conn.close()
