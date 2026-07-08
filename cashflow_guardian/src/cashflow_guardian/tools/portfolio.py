from typing import Optional, Dict, Any, List
import cashflow_guardian.data_engine as de
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk

def make_safe_error(
    error_code: str,
    message: str,
    retryable: bool = False,
    invalid_fields: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None
) -> Dict[str, Any]:
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "invalid_fields": invalid_fields or [],
        "warnings": warnings or []
    }

def get_portfolio_snapshot_tool(
    as_of_month: str,
    industry: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Retrieves portfolio snapshot for a specific month and enriches records with risk scores.
    
    Restricted to a maximum limit of 100 records for performance.
    """
    warnings_list = []
    
    # Restrict limit to a maximum of 100 records
    if limit > 100:
        warnings_list.append("Portfolio-wide risk scoring is restricted to the first 100 records to maintain performance.")
        limit = 100
    if limit < 1:
        limit = 100
        
    try:
        snapshot = de.repository.get_portfolio_snapshot(
            as_of_month=as_of_month,
            industry=industry,
            region=region,
            limit=limit
        )
        
        records = []
        for rec in snapshot.records:
            risk_score = 0.0
            risk_tier = "GREEN"
            evidence = []
            
            # Enrich with risk score if data quality allows
            if rec.data_quality_status != "BLOCKED":
                try:
                    res = score_cashflow_risk(rec.business_id, as_of_month)
                    risk_score = res["risk_score"]
                    risk_tier = res["risk_tier"]
                except Exception as e:
                    warnings_list.append(f"Failed to score business {rec.business_id}: {str(e)}")
                    risk_tier = "unavailable"
                    
            # Compute principal evidence deterministically
            if rec.maximum_days_past_due > 0:
                evidence.append("Active Delinquency")
            if rec.credit_utilization_ratio > 0.70:
                evidence.append("High Credit Utilization")
            if rec.late_invoice_rate > 0.15:
                evidence.append("High Late Invoice Rate")
            if rec.scheduled_debt_service > 0.0:
                # repayment burden ratio
                inf = rec.cash_inflow
                if inf > 0.0 and (rec.scheduled_debt_service / inf) > 0.25:
                    evidence.append("High Repayment Burden")
                    
            if not evidence:
                evidence.append("Stable cash flows")
                
            records.append({
                "business_id": rec.business_id,
                "business_name": rec.business_name,
                "risk_tier": risk_tier,
                "risk_score": float(risk_score),
                "principal_evidence": evidence,
                "data_quality_status": rec.data_quality_status
            })
            
        return {
            "status": "success",
            "as_of_month": snapshot.as_of_month,
            "summary": {
                "total_businesses_scanned": len(records),
                "red_alert_count": sum(1 for r in records if r["risk_tier"] == "RED"),
                "amber_alert_count": sum(1 for r in records if r["risk_tier"] == "AMBER"),
                "green_alert_count": sum(1 for r in records if r["risk_tier"] == "GREEN")
            },
            "records": records,
            "provenance": snapshot.provenance.model_dump(),
            "warnings": warnings_list + snapshot.provenance.warnings
        }
        
    except ValueError as e:
        return make_safe_error("INVALID_ARGUMENTS", str(e), warnings=warnings_list)
    except ConnectionError as e:
        return make_safe_error("DATABASE_ERROR", "The database is temporarily unreachable.", retryable=True, warnings=warnings_list)
    except Exception as e:
        return make_safe_error("INTERNAL_ERROR", "An internal system error occurred.", warnings=warnings_list)
