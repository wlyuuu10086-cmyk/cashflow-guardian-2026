import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from .schemas import FeatureContribution, RiskExplanation
from .model_loader import load_feature_columns
import cashflow_guardian.data_engine as de

def get_lr_contributions(calibrated_lr: Any, X_row: pd.DataFrame) -> List[FeatureContribution]:
    """Calculates local feature contributions for Logistic Regression.
    
    Contribution = scaled_value * coefficient.
    Categorical one-hot features are grouped back to their original column names by summation.
    """
    try:
        # Extract pipeline from CalibratedClassifierCV
        pipeline = calibrated_lr.estimator
        prep = pipeline.named_steps['prep']
        clf = pipeline.named_steps['clf']
        
        # Transform the single row
        X_trans = prep.transform(X_row)[0]
        
        # Get coefficients
        coefs = clf.coef_[0]
        
        # Map back to original feature columns
        num_feats = prep.transformers_[0][2]
        cat_feats = prep.transformers_[1][2]
        ohe = prep.named_transformers_['cat']
        ohe_names = ohe.get_feature_names_out(cat_feats)
        
        all_trans_names = list(num_feats) + list(ohe_names)
        
        # Compute raw contributions
        contribs = X_trans * coefs
        
        # Group by original columns
        grouped_contribs: Dict[str, float] = {}
        
        # Numerical features map 1-to-1
        for i, name in enumerate(num_feats):
            grouped_contribs[name] = float(contribs[i])
            
        # Categorical features need grouping
        offset = len(num_feats)
        for i, ohe_name in enumerate(ohe_names):
            contrib_val = float(contribs[offset + i])
            # Find which original category name this belongs to
            matched = False
            for orig_cat in cat_feats:
                if ohe_name.startswith(orig_cat + "_"):
                    grouped_contribs[orig_cat] = grouped_contribs.get(orig_cat, 0.0) + contrib_val
                    matched = True
                    break
            if not matched:
                grouped_contribs[ohe_name] = contrib_val
                
        return [FeatureContribution(feature_name=k, contribution_value=v) for k, v in grouped_contribs.items()]
    except Exception as e:
        # Fallback to empty if error occurs during introspection
        return []

def generate_explanation(
    business_id: str,
    month: str,
    risk_score: float,
    risk_tier: str,
    feature_vector: Dict[str, float],
    model_type: str,
    calibrated_model: Optional[Any] = None
) -> RiskExplanation:
    """Compiles observed facts, deterministic metrics, predictions, contributions and interpretations."""
    
    # 1. Observed facts
    observed_facts = {
        "business_id": business_id,
        "as_of_month": month,
        "ending_cash_balance": feature_vector.get("ending_cash_balance", 0.0),
        "avg_daily_balance": feature_vector.get("avg_daily_balance", 0.0),
        "overdraft_days": int(feature_vector.get("overdraft_days", 0)),
        "max_dpd": int(feature_vector.get("max_dpd", 0)),
        "payroll_amount": feature_vector.get("payroll_amount", 0.0),
        "scheduled_debt_service": feature_vector.get("scheduled_debt_service", 0.0),
        "actual_debt_service": feature_vector.get("actual_debt_service", 0.0)
    }
    
    # 2. Deterministic derived metrics
    inflow = feature_vector.get("cash_inflow", 0.0)
    repay_burden = (observed_facts["scheduled_debt_service"] / inflow) if inflow > 0 else 0.0
    payroll_burden = (observed_facts["payroll_amount"] / inflow) if inflow > 0 else 0.0
    margin = (feature_vector.get("net_cash_flow", 0.0) / inflow) if inflow > 0 else 0.0
    
    deterministic_metrics = {
        "repayment_burden_ratio": repay_burden,
        "payroll_burden_ratio": payroll_burden,
        "margin": margin,
        "consecutive_negative_cash_flow_months": int(feature_vector.get("consecutive_negative_cash_flow_months", 0)),
        "industry_margin_delta": feature_vector.get("industry_margin_gap", 0.0),
        "industry_collection_days_delta": feature_vector.get("industry_collection_days_gap", 0.0),
        "industry_volatility_ratio": feature_vector.get("industry_volatility_ratio", 0.0)
    }
    
    # 3. Model predictions
    model_predictions = {
        "model_type": model_type,
        "calibrated_risk_score": risk_score,
        "assigned_risk_tier": risk_tier
    }
    
    # 4. Local model contributions
    local_contributions: List[FeatureContribution] = []
    if model_type == "logistic_regression" and calibrated_model is not None:
        # Convert feature vector dict back to single row DataFrame
        try:
            # Load schema columns
            schema_cols = load_feature_columns()
            num_cols = schema_cols["numerical_features"]
            cat_cols = schema_cols["categorical_features"]
            
            # Retrieve business details for categorical variables
            conn = de.get_readonly_connection()
            cust_details = conn.execute(
                "SELECT industry, region, revenue_band, legal_structure FROM business_customers WHERE business_id = ?",
                (business_id,)
            ).fetchone()
            conn.close()
            
            if cust_details:
                row_dict = {k: [feature_vector.get(k, 0.0)] for k in num_cols}
                row_dict["industry"] = [cust_details[0]]
                row_dict["region"] = [cust_details[1]]
                row_dict["revenue_band"] = [cust_details[2]]
                row_dict["legal_structure"] = [cust_details[3]]
                
                X_row = pd.DataFrame(row_dict)
                local_contributions = get_lr_contributions(calibrated_model, X_row)
        except Exception:
            pass
            
    # 5. Derived interpretations
    interpretations = []
    if repay_burden >= 0.40:
        interpretations.append("CRITICAL: Monthly scheduled debt service exceeds 40% of cash inflow.")
    elif repay_burden >= 0.25:
        interpretations.append("WARNING: Repayment burden is elevated, exceeding 25% of cash inflow.")
        
    if observed_facts["overdraft_days"] >= 5:
        interpretations.append("CRITICAL: Severe overdraft persistence with 5+ days in overdraft.")
    elif observed_facts["overdraft_days"] >= 2:
        interpretations.append("WARNING: Frequent overdraft triggers observed (2+ days).")
        
    neg_streak = deterministic_metrics["consecutive_negative_cash_flow_months"]
    if neg_streak >= 3:
        interpretations.append(f"WARNING: Persistent negative cash flow streak for {neg_streak} consecutive months.")
        
    coll_gap = deterministic_metrics["industry_collection_days_delta"]
    if coll_gap >= 30.0:
        interpretations.append("CRITICAL: Collection delays exceed industry average by more than 30 days.")
    elif coll_gap >= 15.0:
        interpretations.append("WARNING: Invoice collections are delayed by 15+ days compared to industry average.")
        
    # Non-causal declaration
    interpretations.append("Disclaimer: This early warning risk signal indicates statistical correlation based on historical baseline trends; it does not claim direct physical causality.")
    
    return RiskExplanation(
        business_id=business_id,
        month=month,
        risk_score=risk_score,
        risk_tier=risk_tier,
        observed_facts=observed_facts,
        deterministic_metrics=deterministic_metrics,
        model_predictions=model_predictions,
        local_contributions=local_contributions,
        interpretations=interpretations
    )
