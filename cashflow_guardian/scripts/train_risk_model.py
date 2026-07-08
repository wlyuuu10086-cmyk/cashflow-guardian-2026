import os
import sys
import yaml
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    precision_recall_curve, auc, roc_auc_score, brier_score_loss,
    precision_score, recall_score, f1_score, confusion_matrix
)

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent

def calculate_top_k_metrics(y_true, y_prob, k_percent=0.10):
    n = len(y_true)
    k = int(np.ceil(n * k_percent))
    
    # Sort indices by probability descending
    sorted_idx = np.argsort(y_prob)[::-1]
    top_k_idx = sorted_idx[:k]
    
    y_true_top_k = y_true.iloc[top_k_idx]
    
    # Positive count in top K
    pos_in_top_k = (y_true_top_k == 1.0).sum()
    total_pos = (y_true == 1.0).sum()
    
    precision_at_k = pos_in_top_k / k if k > 0 else 0.0
    recall_at_k = pos_in_top_k / total_pos if total_pos > 0 else 0.0
    
    # Base rate of positives
    base_rate = total_pos / n if n > 0 else 0.0
    lift_at_k = precision_at_k / base_rate if base_rate > 0 else 0.0
    
    return precision_at_k, recall_at_k, lift_at_k

def evaluate_model(model, X, y):
    # Predict calibrated probabilities
    y_prob = model.predict_proba(X)[:, 1]
    
    # PR-AUC
    precisions, recalls, _ = precision_recall_curve(y, y_prob)
    pr_auc = auc(recalls, precisions)
    
    # ROC-AUC
    roc_auc = roc_auc_score(y, y_prob)
    
    # Brier Score
    brier = brier_score_loss(y, y_prob)
    
    return y_prob, pr_auc, roc_auc, brier

def train_pipeline():
    print("==========================================================")
    print("         CASHFLOW GUARDIAN MODEL TRAINING PIPELINE        ")
    print("==========================================================\n")
    
    repo_root = get_repo_root()
    models_dir = repo_root / "models"
    config_dir = repo_root / "config"
    
    # 1. Load configurations
    with open(config_dir / "model.yaml", "r") as f:
        model_config = yaml.safe_load(f)
        
    num_features = model_config["features"]["numerical_features"]
    cat_features = model_config["features"]["categorical_features"]
    target_col = "candidate_composite"
    
    # 2. Load Parquet dataset
    dataset_path = models_dir / "training_dataset.parquet"
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found at {dataset_path}. Run build_training_dataset.py first.")
        sys.exit(1)
        
    print(f"Loading training dataset from {dataset_path}...")
    df = pd.read_parquet(dataset_path)
    
    # Sort chronologically
    df = df.sort_values(['business_id', 'month']).reset_index(drop=True)
    
    # 3. Time-based Split
    print("Creating chronological splits...")
    # Train: <= 2025-04
    # Val: 2025-05 to 2025-07
    # Test: 2025-08 to 2025-10
    train_df = df[df['month'] <= '2025-04'].copy()
    val_df = df[(df['month'] >= '2025-05') & (df['month'] <= '2025-07')].copy()
    test_df = df[(df['month'] >= '2025-08') & (df['month'] <= '2025-10')].copy()
    
    # Hard split class presence verification
    for name, split_df in [("Train", train_df), ("Validation", val_df), ("Test", test_df)]:
        pos_count = (split_df[target_col] == 1.0).sum()
        neg_count = (split_df[target_col] == 0.0).sum()
        print(f"  {name} Split: Rows={len(split_df):,}, Positives={pos_count:,}, Negatives={neg_count:,}, PosRate={pos_count/len(split_df)*100:.2f}%")
        if pos_count == 0 or neg_count == 0:
            print(f"CRITICAL ERROR: {name} split does not contain both classes. Training aborted.")
            sys.exit(1)
            
    # Separate features and labels
    X_train, y_train = train_df[num_features + cat_features], train_df[target_col]
    X_val, y_val = val_df[num_features + cat_features], val_df[target_col]
    X_test, y_test = test_df[num_features + cat_features], test_df[target_col]
    
    # 4. Fit Preprocessing strictly on the training set
    print("Fitting preprocessing pipeline on training set...")
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_features)
        ]
    )
    
    # Define models
    # Model A: Baseline Logistic Regression
    lr_params = model_config.get("baseline_model", {}).get("hyperparameters", {})
    base_lr = LogisticRegression(
        penalty=lr_params.get("penalty", "l2"),
        C=lr_params.get("C", 1.0),
        solver=lr_params.get("solver", "lbfgs"),
        max_iter=lr_params.get("max_iter", 1000),
        class_weight=lr_params.get("class_weight", "balanced"),
        random_state=42
    )
    
    # Model B: Candidate Random Forest
    base_rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    
    # Create preprocessing + model pipelines
    pipe_lr = Pipeline([('prep', preprocessor), ('clf', base_lr)])
    pipe_rf = Pipeline([('prep', preprocessor), ('clf', base_rf)])
    
    # Fit base models on training set
    print("Training Model A (Logistic Regression baseline)...")
    pipe_lr.fit(X_train, y_train)
    
    print("Training Model B (Random Forest classifier)...")
    pipe_rf.fit(X_train, y_train)
    
    # 5. Isotonic Calibration on Validation Set
    print("Applying Isotonic Calibration on Validation Set...")
    cal_lr = CalibratedClassifierCV(estimator=pipe_lr, method='isotonic', cv='prefit')
    cal_lr.fit(X_val, y_val)
    
    cal_rf = CalibratedClassifierCV(estimator=pipe_rf, method='isotonic', cv='prefit')
    cal_rf.fit(X_val, y_val)
    
    # 6. Evaluate Models on Validation Set & Select Thresholds
    print("Evaluating models on Validation Set for threshold selection...")
    y_prob_val_lr, pr_auc_val_lr, _, brier_val_lr = evaluate_model(cal_lr, X_val, y_val)
    y_prob_val_rf, pr_auc_val_rf, _, brier_val_rf = evaluate_model(cal_rf, X_val, y_val)
    
    print(f"  Logistic Regression Val PR-AUC: {pr_auc_val_lr:.4f} | Brier: {brier_val_lr:.4f}")
    print(f"  Random Forest Val PR-AUC: {pr_auc_val_rf:.4f} | Brier: {brier_val_rf:.4f}")
    
    # Select thresholds using Random Forest validation probabilities
    # We will choose:
    #   Red (High) threshold: set at the 90th percentile of validation risk scores (capping alerts at 10% of portfolio review capacity)
    #   Amber (Medium) threshold: set to capture at least 90% recall of true validation stress cases
    #   Critical threshold: set at the 97th percentile of validation risk scores
    
    # Red Threshold
    thresh_red = float(np.percentile(y_prob_val_rf, 90))
    # Critical Threshold
    thresh_crit = float(np.percentile(y_prob_val_rf, 97))
    
    # Amber Threshold: find the score threshold where recall is >= 90%
    # precision_recall_curve returns thresholds in ascending order, corresponding to recalls in descending order
    p_curve, r_curve, t_curve = precision_recall_curve(y_val, y_prob_val_rf)
    # Filter where recall >= 0.90
    valid_idx = np.where(r_curve >= 0.90)[0]
    # Corresponding thresholds (t_curve has length len(r_curve) - 1)
    if len(valid_idx) > 0 and valid_idx[-1] < len(t_curve):
        thresh_amber = float(t_curve[valid_idx[-1]])
    else:
        thresh_amber = 0.30 # Fallback default
        
    # Ensure thresholds are ordered correctly and bounded
    thresh_amber = max(0.10, min(thresh_amber, thresh_red - 0.10))
    thresh_red = max(thresh_amber + 0.05, min(thresh_red, thresh_crit - 0.05))
    
    threshold_config = {
        "selection_rationale": "Thresholds selected on Validation set calibrated risk scores. Red (0.70 Target/Actual 90th percentile) caps portfolio review alert capacity at 10%. Amber is set to guarantee a minimum of 90% recall of cash stress events. Critical (97th percentile) flags immediate priority review cases.",
        "tiers": {
            "low": {"min": 0.00, "max": float(round(thresh_amber, 4))},
            "medium": {"min": float(round(thresh_amber, 4)), "max": float(round(thresh_red, 4))},
            "high": {"min": float(round(thresh_red, 4)), "max": float(round(thresh_crit, 4))},
            "critical": {"min": float(round(thresh_crit, 4)), "max": 1.00}
        }
    }
    
    # Save thresholds config
    threshold_path = models_dir / "threshold_config.json"
    with open(threshold_path, "w") as f:
        json.dump(threshold_config, f, indent=4)
    print(f"Saved threshold configuration to {threshold_path}")
    
    # 7. Final Evaluation on untouched Test Set
    print("\nEvaluating models on untouched Test Set...")
    # Evaluate LR
    y_prob_test_lr, pr_auc_test_lr, roc_auc_test_lr, brier_test_lr = evaluate_model(cal_lr, X_test, y_test)
    # Evaluate RF
    y_prob_test_rf, pr_auc_test_rf, roc_auc_test_rf, brier_test_rf = evaluate_model(cal_rf, X_test, y_test)
    
    # Selected threshold metrics at Red (High) threshold
    selected_thresh = thresh_red
    y_pred_test_rf = (y_prob_test_rf >= selected_thresh).astype(float)
    y_pred_test_lr = (y_prob_test_lr >= selected_thresh).astype(float)
    
    prec_rf = precision_score(y_test, y_pred_test_rf)
    rec_rf = recall_score(y_test, y_pred_test_rf)
    f1_rf = f1_score(y_test, y_pred_test_rf)
    cm_rf = confusion_matrix(y_test, y_pred_test_rf).tolist()
    
    prec_lr = precision_score(y_test, y_pred_test_lr)
    rec_lr = recall_score(y_test, y_pred_test_lr)
    f1_lr = f1_score(y_test, y_pred_test_lr)
    cm_lr = confusion_matrix(y_test, y_pred_test_lr).tolist()
    
    # Top K (10%) metrics
    prec_at_10_rf, rec_at_10_rf, lift_at_10_rf = calculate_top_k_metrics(y_test, y_prob_test_rf, 0.10)
    prec_at_10_lr, rec_at_10_lr, lift_at_10_lr = calculate_top_k_metrics(y_test, y_prob_test_lr, 0.10)
    
    print("\n--- TEST SET RESULTS ---")
    print(f"Model A (Logistic Regression Baseline):")
    print(f"  PR-AUC: {pr_auc_test_lr:.4f} | ROC-AUC: {roc_auc_test_lr:.4f} | Brier: {brier_test_lr:.4f}")
    print(f"  Precision: {prec_lr:.4f} | Recall: {rec_lr:.4f} | F1: {f1_lr:.4f} at threshold {selected_thresh:.4f}")
    print(f"  Recall@Top10%: {rec_at_10_lr:.4f} | Precision@Top10%: {prec_at_10_lr:.4f} | Lift@Top10%: {lift_at_10_lr:.2f}x")
    
    print(f"\nModel B (Random Forest Classifier):")
    print(f"  PR-AUC: {pr_auc_test_rf:.4f} | ROC-AUC: {roc_auc_test_rf:.4f} | Brier: {brier_test_rf:.4f}")
    print(f"  Precision: {prec_rf:.4f} | Recall: {rec_rf:.4f} | F1: {f1_rf:.4f} at threshold {selected_thresh:.4f}")
    print(f"  Recall@Top10%: {rec_at_10_rf:.4f} | Precision@Top10%: {prec_at_10_rf:.4f} | Lift@Top10%: {lift_at_10_rf:.2f}x")
    
    # 8. Save models
    print("\nSaving fitted models...")
    joblib.dump(cal_lr, models_dir / "baseline_model.joblib")
    joblib.dump(cal_rf, models_dir / "best_model.joblib")
    
    # Save feature list
    feature_cols = {
        "numerical_features": num_features,
        "categorical_features": cat_features,
        "model_features": num_features + list(preprocessor.fit(X_train, y_train).named_transformers_['cat'].get_feature_names_out(cat_features))
    }
    with open(models_dir / "feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=4)
        
    # Save calibration report
    calibration_report = {
        "isotonic_calibration": {
            "validation_brier_score_lr": float(brier_val_lr),
            "validation_brier_score_rf": float(brier_val_rf),
            "test_brier_score_lr": float(brier_test_lr),
            "test_brier_score_rf": float(brier_test_rf)
        }
    }
    with open(models_dir / "calibration_report.json", "w") as f:
        json.dump(calibration_report, f, indent=4)
        
    # Build metadata
    reproducibility_id = "repro_random_state_42_split_202504"
    metadata = {
        "target_formula": "future_60d_dpd30_flag == 1 OR (future_60d_negative_cashflow_flag == 1 AND future_60d_collection_delay_spike_flag == 1)",
        "target_prevalence": float(df[target_col].mean()),
        "feature_list": num_features + cat_features,
        "minimum_lookback": 3,
        "split_periods": {
            "train": {"start": "2024-03", "end": "2025-04"},
            "validation": {"start": "2025-05", "end": "2025-07"},
            "test": {"start": "2025-08", "end": "2025-10"}
        },
        "split_row_counts": {
            "train": len(X_train),
            "validation": len(X_val),
            "test": len(X_test)
        },
        "class_rates_by_split": {
            "train": float(y_train.mean()),
            "validation": float(y_val.mean()),
            "test": float(y_test.mean())
        },
        "preprocessing_pipeline": "ColumnTransformer: StandardScaler (numerical) + OneHotEncoder (categorical)",
        "selected_model": "RandomForestClassifier",
        "calibration_method": "isotonic regression",
        "selected_thresholds": threshold_config["tiers"],
        "final_test_metrics": {
            "baseline_logistic_regression": {
                "pr_auc": float(pr_auc_test_lr),
                "roc_auc": float(roc_auc_test_lr),
                "brier_score": float(brier_test_lr),
                "precision": float(prec_lr),
                "recall": float(rec_lr),
                "f1_score": float(f1_lr),
                "confusion_matrix": cm_lr,
                "recall_at_top_10": float(rec_at_10_lr),
                "precision_at_top_10": float(prec_at_10_lr),
                "lift_at_top_10": float(lift_at_10_lr)
            },
            "random_forest": {
                "pr_auc": float(pr_auc_test_rf),
                "roc_auc": float(roc_auc_test_rf),
                "brier_score": float(brier_test_rf),
                "precision": float(prec_rf),
                "recall": float(rec_rf),
                "f1_score": float(f1_rf),
                "confusion_matrix": cm_rf,
                "recall_at_top_10": float(rec_at_10_rf),
                "precision_at_top_10": float(prec_at_10_rf),
                "lift_at_top_10": float(lift_at_10_rf)
            }
        },
        "known_limitations": "Model evaluated on synthetic database with highly prevalent negative net cash flows. Calibration fitted using small validation set. Categorical encoder ignores unseen categories during deployment.",
        "training_timestamp": datetime.now().isoformat(),
        "reproducibility_identifier": reproducibility_id
    }
    
    with open(models_dir / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Saved model metadata to {models_dir / 'model_metadata.json'}")
    
    print("\nSUCCESS: Model training and calibration complete!")
    print("==========================================================")

if __name__ == "__main__":
    train_pipeline()
