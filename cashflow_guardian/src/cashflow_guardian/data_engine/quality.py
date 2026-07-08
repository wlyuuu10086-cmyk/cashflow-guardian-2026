import duckdb
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from .connection import get_readonly_connection
from .schemas import DataQualityResult, ProvenanceMetadata
from .provenance import build_provenance
from .validators import validate_business_id, validate_as_of_month, ValidationError

def check_business_data_quality(business_id: str, as_of_month: str) -> DataQualityResult:
    """Evaluates data presence, duplicates, null counts, and history duration for a business.
    
    Returns DataQualityResult.
    """
    errors: List[str] = []
    warnings: List[str] = []
    missing_fields: List[str] = []
    missing_months: List[str] = []
    transaction_gaps = False
    has_sufficient_history = False
    can_build_features = True
    status = "COMPLETED"
    
    conn = None
    try:
        conn = get_readonly_connection()
        
        # 1. Validate ID and Month existence & format
        try:
            validate_business_id(business_id, conn)
        except ValidationError as e:
            errors.append(str(e))
            return DataQualityResult(
                status="BLOCKED",
                can_build_features=False,
                missing_fields=[],
                missing_months=[],
                transaction_gaps=False,
                has_sufficient_history=False,
                errors=errors,
                warnings=warnings
            )
            
        try:
            validate_as_of_month(as_of_month, conn)
        except ValidationError as e:
            errors.append(str(e))
            return DataQualityResult(
                status="BLOCKED",
                can_build_features=False,
                missing_fields=[],
                missing_months=[],
                transaction_gaps=False,
                has_sufficient_history=False,
                errors=errors,
                warnings=warnings
            )
        
        # 2. Query history up to and including as_of_month
        snapshots = conn.execute(
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
            ORDER BY month ASC
            """,
            (business_id, as_of_month)
        ).fetchall()
        
        # Build column map for easy index reference
        columns = [
            "month", "opening_cash_balance_proxy", "ending_cash_balance_proxy",
            "avg_daily_balance_proxy", "overdraft_days_proxy", "transaction_count",
            "cash_inflow_observed", "cash_outflow_observed", "net_cash_flow_observed",
            "invoice_count", "invoice_amount_total", "avg_days_to_pay",
            "late_invoice_rate", "payroll_amount", "employee_count",
            "scheduled_debt_service", "actual_debt_service", "max_dpd",
            "available_credit_drawn_ratio"
        ]
        col_idx = {name: i for i, name in enumerate(columns)}
        
        # 3. Check for duplicates in snapshots
        dup_rows = conn.execute(
            """
            SELECT month, COUNT(*) 
            FROM business_monthly_snapshots 
            WHERE business_id = ? AND month <= ? 
            GROUP BY month 
            HAVING COUNT(*) > 1
            """,
            (business_id, as_of_month)
        ).fetchall()
        if dup_rows:
            errors.append(f"Duplicate business-month rows found: {', '.join([r[0] for r in dup_rows])}")
            can_build_features = False
            status = "BLOCKED"
        
        # 4. Check for target month snapshot presence
        target_snapshot = None
        for s in snapshots:
            if s[col_idx["month"]] == as_of_month:
                target_snapshot = s
                break
                
        if not target_snapshot:
            errors.append(f"Missing snapshot for target month '{as_of_month}'")
            can_build_features = False
            status = "BLOCKED"
            
        # 5. Check history completeness (at least 3 months required including target month)
        history_len = len(snapshots)
        if history_len >= 3:
            has_sufficient_history = True
        else:
            warnings.append(f"Insufficient history to calculate features ({history_len} month observed, 3 months required)")
            can_build_features = False
            if status != "BLOCKED":
                status = "WARNING"
            
        # 6. Check for transaction gaps (a month with zero transactions after onboarding)
        for s in snapshots:
            tx_count = s[col_idx["transaction_count"]]
            if tx_count == 0 or tx_count is None:
                transaction_gaps = True
                warnings.append(f"Transaction gap: 0 transactions in month {s[col_idx['month']]}")
                
        # 7. Audit target month columns (if snapshot exists)
        if target_snapshot:
            # Required fields: ending balance, opening balance, cash inflow, cash outflow
            required_fields = [
                "opening_cash_balance_proxy", "ending_cash_balance_proxy",
                "cash_inflow_observed", "cash_outflow_observed"
            ]
            for field in required_fields:
                val = target_snapshot[col_idx[field]]
                if val is None:
                    missing_fields.append(field)
                    errors.append(f"Missing required financial field: '{field}'")
                    can_build_features = False
                    status = "BLOCKED"
            
            # Optional / Activity fields: lack of these must not block feature construction
            # We flag them as informational warnings only
            optional_fields = {
                "invoice_amount_total": "invoicing",
                "payroll_amount": "payroll",
                "scheduled_debt_service": "loan/repayment"
            }
            for field, activity in optional_fields.items():
                val = target_snapshot[col_idx[field]]
                if val is None or val == 0.0:
                    warnings.append(f"Optional {activity} data is absent (informational only).")
        
        # 8. Check for missing months in history (gaps in month sequence)
        if history_len > 1:
            # Parse month strings into year, month integers to check gaps
            def month_to_num(m_str: str) -> int:
                y, m = map(int, m_str.split("-"))
                return y * 12 + m
                
            sorted_months = sorted([s[col_idx["month"]] for s in snapshots])
            nums = [month_to_num(m) for m in sorted_months]
            for idx in range(len(nums) - 1):
                diff = nums[idx+1] - nums[idx]
                if diff > 1:
                    # There is a month gap
                    curr_num = nums[idx] + 1
                    while curr_num < nums[idx+1]:
                        gap_y = curr_num // 12
                        gap_m = curr_num % 12
                        if gap_m == 0:
                            gap_y -= 1
                            gap_m = 12
                        missing_months.append(f"{gap_y:04d}-{gap_m:02d}")
                        curr_num += 1
            if missing_months:
                warnings.append(f"Gaps detected in history. Missing months: {', '.join(missing_months)}")
                if status != "BLOCKED":
                    status = "WARNING"
                
        # Build provenance
        prov = build_provenance(
            source_tables=["business_customers", "business_monthly_snapshots"],
            as_of_month=as_of_month,
            row_count=history_len,
            warnings=warnings + errors
        )
        
        return DataQualityResult(
            status=status,
            can_build_features=can_build_features,
            missing_fields=missing_fields,
            missing_months=missing_months,
            transaction_gaps=transaction_gaps,
            has_sufficient_history=has_sufficient_history,
            errors=errors,
            warnings=warnings,
            provenance=prov
        )
        
    except Exception as e:
        errs = errors + [f"Unexpected error checking data quality: {e}"]
        return DataQualityResult(
            status="BLOCKED",
            can_build_features=False,
            missing_fields=missing_fields,
            missing_months=missing_months,
            transaction_gaps=transaction_gaps,
            has_sufficient_history=has_sufficient_history,
            errors=errs,
            warnings=warnings
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
