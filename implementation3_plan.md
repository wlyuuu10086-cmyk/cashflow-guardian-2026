# Implementation Plan - Risk Engine Design & Baseline Modeling

This plan outlines the design and implementation of the CashFlow Guardian Risk Engine (Step 4 of the Capstone). We define the dataset building process, baseline modeling (Logistic Regression and XGBoost), probability calibration, risk scoring engine, explanation layer, and validation steps.

## User Review Required

> [!IMPORTANT]
> **Key Design Decisions & Observations:**
> 1. **Target Label:** We will use `future_60d_cash_stress_observed` as the target label. It is heavily skewed (97.0% positive rate, i.e., cash flow stress is the majority class). Therefore, the modeling goal is effectively predicting the rare "healthy" state (0) vs the common "stressed" state (1).
> 2. **Evaluation Metrics:** Due to this class imbalance, accuracy is not a valid metric. We will prioritize PR-AUC (Precision-Recall Area Under the Curve) and Recall@TopK (e.g. Top 10% highest risk scores).
> 3. **Model Weighting:** We will use `scale_pos_weight` in XGBoost and `class_weight='balanced'` in Logistic Regression to handle the extreme class ratio.
> 4. **Boundary Truncation:** We will strictly exclude observations from `2025-11` and `2025-12` during dataset construction.
> 5. **Chronological Splitting:** We enforce the following split:
>    * **Train Set:** `2024-01` to `2025-04` (24,000 rows)
>    * **Validation Set:** `2025-05` to `2025-07` (4,500 rows)
>    * **Test Set (Holdout):** `2025-08` to `2025-10` (4,500 rows)
> 6. **Fallback Rule-based Scoring:** As required by `behaviors.feature`, if model weights are missing, the scoring engine must fall back to a deterministic rules-based scoring algorithm.

## Open Questions

> [!NOTE]
> No critical open questions remain, as the project specifications (`model_spec.md`, `thresholds.yaml`, and `behaviors.feature`) provide clear, unambiguous boundaries for the baseline model, XGBoost classifier, validation split, and scoring thresholds.

## Proposed Changes

We will create and modify the following files in the `cashflow_guardian` repository:

### Component: Dataset & Model Training Scripts

#### [NEW] [build_dataset.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/scripts/build_dataset.py)
Builds the feature vector dataset by calling `build_point_in_time_features()` for all business IDs and months. It filters out boundary months and saves `models/training_dataset.parquet` along with a JSON metadata file containing the feature names, label definition, and missingness report.

#### [NEW] [train_baseline.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/scripts/train_baseline.py)
Trains Model A (Logistic Regression) and Model B (XGBoost Classifier) using chronological splitting. It applies probability calibration on the validation set, evaluates performance, and saves both models to `models/logistic_regression.pkl` and `models/xgboost_classifier.pkl` (or `.json`).

### Component: Risk Engine Implementation (`src/cashflow_guardian/risk_engine/`)

#### [MODIFY] [scoring.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/scoring.py)
Implements the risk scoring logic:
* Loads the trained XGBoost model (with fallback to rules-based logic if model file is missing).
* Computes `risk_score` (probability between 0.0 and 1.0).
* Maps risk score to `risk_tier` (Low / Medium / High / Critical) using thresholds from `config/thresholds.yaml` and financial indicators.
* Extracts top feature drivers using feature importance / coefficients.
* Returns `model_version`, `confidence_proxy`, and `future_data_used` (provenance).

#### [NEW] [explanation.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/explanation.py)
Implements the explanation layer:
* Explains the top 3 contributing features.
* Compares features to the peer benchmark (via Data Engine's `get_peer_benchmark`).
* Clearly separates observed facts (actual cash balance, overdraft days), model predictions, and derived interpretations.

### Component: Validation & Reports (`artifacts/`)

#### [NEW] [risk_engine_validation.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/risk_engine_validation.md)
Generates the validation report summarizing performance metrics (PR-AUC, Recall@Top10%, Precision, Brier Score), validation curves, and leakage checks.

---

## Verification Plan

### Automated Tests
* Run a Python test script `tests/test_risk_engine.py` to assert:
  1. `score_cashflow_risk` executes successfully for valid inputs.
  2. The model refuses to score businesses with less than 3 months of history or invalid IDs.
  3. Risk score is bounded between 0 and 1.
  4. Missing model file triggers graceful fallback to rules-based score.
  5. The output has zero future leakage.

### Manual Verification
* Run `scripts/build_dataset.py` and `scripts/train_baseline.py`.
* Review performance numbers in `artifacts/risk_engine_validation.md`.
