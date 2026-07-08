import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

import cashflow_guardian.data_engine as de
from .schemas import RiskScoreResult, FeatureContribution
from .model_loader import (
    load_risk_models, load_feature_columns, load_threshold_config,
    load_model_metadata, ModelLoadingError
)
from .thresholds import map_score_to_tier
from .explanation import generate_explanation
from .monitoring import audit_logger

def calculate_rules_based_fallback(features: Dict[str, float]) -> float:
    """Computes a deterministic cash flow stress score between 0.0 and 1.0.
    
    This is used ONLY as a backup fallback heuristic when the ML model is missing.
    """
    score = 0.0
    
    # 1. Overdraft days: 0.1 per day, capped at 0.4
    overdraft_days = features.get("overdraft", features.get("overdraft_days", 0.0))
    score += min(0.4, overdraft_days * 0.1)
    
    # 2. Repayment burden ratio (scheduled_debt_service / cash_inflow)
    inflow = features.get("cash_inflow", 0.0)
    sched = features.get("scheduled_debt_service", 0.0)
    if inflow > 0:
        repay_burden = sched / inflow
        if repay_burden > 0.40:
            score += 0.4
        elif repay_burden > 0.25:
            score += 0.2
            
    # 3. Payroll burden ratio (payroll_amount / cash_inflow)
    payroll = features.get("payroll_amount", 0.0)
    if inflow > 0:
        payroll_burden = payroll / inflow
        if payroll_burden > 0.50:
            score += 0.2
        elif payroll_burden > 0.35:
            score += 0.1
            
    # 4. Consecutive negative cash flow months: 0.1 per month, capped at 0.3
    neg_months = features.get("consecutive_negative_cash_flow_months", 0.0)
    score += min(0.3, neg_months * 0.1)
    
    return float(round(max(0.0, min(score, 1.0)), 4))

def score_cashflow_risk(business_id: str, month: str) -> Dict[str, Any]:
    """Scores early-warning risk for a business snapshot.
    
    Orchestrates:
      1. Validation of business_id and month boundaries.
      2. Fetching features from Data Engine.
      3. Applying data quality and refusal-to-score conditions.
      4. Scoring via calibrated Random Forest model (Model B) with Logistic Regression (Model A) support.
      5. Falling back to rules-based stress heuristics if models are missing.
    """
    warnings: List[str] = []
    
    # 1. Refusal-to-Score Guard: Boundary Month Validation
    conn_val = de.get_readonly_connection()
    try:
        de.validate_as_of_month(month, conn_val)
    except de.OutOfBoundaryMonthError as e:
        raise ValueError(f"Refusal to score: Requested month {month} is out of bounds.")
    except Exception as e:
        raise ValueError(f"Refusal to score: Invalid month format. {e}")
    finally:
        conn_val.close()
        
    # 2. Fetch point-in-time features from Data Engine
    fv = de.build_point_in_time_features(business_id, month)
    
    # Check invalid business ID from features outcome
    if not fv.features and any("not found" in w.lower() or "invalid" in w.lower() for w in fv.missing_feature_warnings):
        raise ValueError(f"Business ID {business_id} was not found in the database.")
        
    # 3. Refusal-to-Score Guard: Sufficiency of history
    # Verify if history length is less than 3 months
    dq = de.check_business_data_quality(business_id, month)
    if not dq.can_build_features or any("insufficient history" in w.lower() for w in dq.warnings + dq.errors):
        # Retrieve actual count from database
        conn = de.get_readonly_connection()
        history_cnt = conn.execute(
            "SELECT COUNT(*) FROM business_monthly_snapshots WHERE business_id = ? AND month <= ?",
            (business_id, month)
        ).fetchone()[0]
        conn.close()
        raise ValueError(f"Insufficient history to calculate features ({history_cnt} month observed, 3 months required)")
        
    # 4. Refusal-to-Score Guard: Future leakage detection
    if fv.future_data_used or fv.provenance.future_data_used:
        raise ValueError("Security violation: Ingestion of future snapshots detected.")
        
    # 5. Attempt loading models
    best_model = None
    model_meta = None
    feature_cols = None
    
    try:
        # Load risk models and metadata
        _, best_model = load_risk_models()
        model_meta = load_model_metadata()
        feature_cols = load_feature_columns()
    except (ModelLoadingError, FileNotFoundError, ImportError, Exception) as e:
        warnings.append(f"Predictive ML scoring is temporarily unavailable. Displaying rules-based cash-flow stress score instead. (Reason: {e})")
        
    # Fallback Mode
    if best_model is None:
        risk_score = calculate_rules_based_fallback(fv.features)
        low_tier, rag_tier = map_score_to_tier(risk_score)
        
        result = RiskScoreResult(
            business_id=business_id,
            month=month,
            risk_score=risk_score,
            risk_tier=rag_tier,
            model_version=None,
            scoring_mode="rule_based_fallback",
            model_prediction_available=False,
            risk_score_type="heuristic",
            feature_contributions=[],
            local_contextual_evidence={
                "local_contextual_evidence": {
                    "overdraft_days": int(fv.features.get("overdraft_days", 0)),
                    "consecutive_negative_cash_flow_months": int(fv.features.get("consecutive_negative_cash_flow_months", 0))
                }
            },
            warnings=warnings
        )
        
        # Log entry
        audit_logger.log_prediction(
            business_id=business_id,
            month=month,
            risk_score=risk_score,
            risk_tier=rag_tier,
            scoring_mode="rule_based_fallback",
            warnings=warnings
        )
        
        return result.model_dump()
        
    # 6. ML Scoring Mode
    try:
        # Align feature columns
        num_cols = feature_cols["numerical_features"]
        cat_cols = feature_cols["categorical_features"]
        
        # Build single row DataFrame matching pipeline expectation
        row_dict = {k: [fv.features.get(k, 0.0)] for k in num_cols}
        
        # Fetch categorical data from DB
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
        
        # Verify columns match training list
        expected_features = num_cols + cat_cols
        if not all(col in X_row.columns for col in expected_features):
            raise ValueError("Feature columns discrepancy between model metadata and scoring vector.")
            
        # Predict probability
        risk_score = float(best_model.predict_proba(X_row)[0, 1])
        low_tier, rag_tier = map_score_to_tier(risk_score)
        
        # Local contextual evidence (gaps from peer benchmark)
        local_evidence = {
            "local_contextual_evidence": {
                "industry_margin_delta": fv.features.get("industry_margin_gap", 0.0),
                "industry_collection_days_delta": fv.features.get("industry_collection_days_gap", 0.0),
                "industry_volatility_ratio": fv.features.get("industry_volatility_ratio", 0.0)
            }
        }
        
        result = RiskScoreResult(
            business_id=business_id,
            month=month,
            risk_score=risk_score,
            risk_tier=rag_tier,
            model_version=model_meta.get("selected_model", "RandomForest"),
            scoring_mode="ml_model",
            model_prediction_available=True,
            risk_score_type="calibrated",
            feature_contributions=[],
            local_contextual_evidence=local_evidence,
            warnings=warnings
        )
        
        # Log prediction
        audit_logger.log_prediction(
            business_id=business_id,
            month=month,
            risk_score=risk_score,
            risk_tier=rag_tier,
            scoring_mode="ml_model",
            warnings=warnings
        )
        
        return result.model_dump()
        
    except Exception as e:
        # Fallback in case of prediction execution failures
        warnings.append(f"Model prediction failed. Displaying rules-based fallback. (Error: {e})")
        risk_score = calculate_rules_based_fallback(fv.features)
        low_tier, rag_tier = map_score_to_tier(risk_score)
        
        result = RiskScoreResult(
            business_id=business_id,
            month=month,
            risk_score=risk_score,
            risk_tier=rag_tier,
            model_version=None,
            scoring_mode="rule_based_fallback",
            model_prediction_available=False,
            risk_score_type="heuristic",
            feature_contributions=[],
            local_contextual_evidence={
                "local_contextual_evidence": {
                    "overdraft_days": int(fv.features.get("overdraft_days", 0)),
                    "consecutive_negative_cash_flow_months": int(fv.features.get("consecutive_negative_cash_flow_months", 0))
                }
            },
            warnings=warnings
        )
        
        return result.model_dump()
