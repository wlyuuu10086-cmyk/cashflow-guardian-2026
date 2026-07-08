# Implementation Plan - Risk Engine Design & Baseline Modeling (Revised)

This implementation plan details the corrected strategy for Step 4 of the Capstone (Risk Engine Design + Baseline Modeling), satisfying all 16 mandatory corrections requested.

## User Review Required

> [!IMPORTANT]
> **Key Design Decisions & Corrected Strategies:**
>
> 1. **Target Label Candidate Selection:**
>    Based on the label audit, the precalculated `future_60d_cash_stress_observed` has a ~97.0% positive rate (due to the prevalence of negative cash flows in the synthetic data), making it non-discriminative.
>    We select **Candidate Composite Target** as the MVP target:
>    $$\text{Target} = \text{future\_60d\_dpd30\_flag} == 1 \lor (\text{future\_60d\_negative\_cashflow\_flag} == 1 \land \text{future\_60d\_collection\_delay\_spike\_flag} == 1)$$
>    This target has 4,562 positive cases (13.82% prevalence), represents a compound credit-liquidity squeeze, and is highly discriminative.
>
> 2. **Batch Dataset Building:**
>    Instead of tens of thousands of individual database round trips, we will implement an efficient batch feature-building path in `scripts/build_training_dataset.py`. It loads all relevant snapshots and benchmark data, performs vectorized window operations (rolling 3m mean, sample standard deviation, lag differences) in pandas, and saves to `models/training_dataset.parquet`.
>    *Consistency check:* We will validate correctness by comparing a sample of batch-built feature rows against single-record outputs from `build_point_in_time_features()`.
>
> 3. **Model Choices & Preprocessing:**
>    * **Model A (Mandatory Baseline):** `LogisticRegression` (L2 regularized) fitted with StandardScaler. Preprocessing parameters (means, variances) will be fit **strictly** on the training split and applied to validation/test.
>    * **Model B (Tree-based comparison):** `RandomForestClassifier` from scikit-learn. XGBoost is not pre-installed in the environment, and LightGBM is prohibited.
>
> 4. **Chronological Splitting & Leakage Prevention:**
>    * **Train Period:** `2024-01` to `2025-04` (requires first 3 months as lookback history, meaning features are calculated starting from `2024-03`).
>    * **Validation Period:** `2025-05` to `2025-07` (used for probability calibration and threshold selection).
>    * **Test Period (Holdout):** `2025-08` to `2025-10` (strictly untouched until final validation).
>    * *Boundary Truncation:* Months `2025-11` and `2025-12` are completely excluded since outcomes are not fully observable.
>
> 5. **Calibration & Threshold Selection:**
>    * Base models are fit on training data.
>    * Validation split is used for probability calibration (`CalibratedClassifierCV` or manual isotopic regression) and threshold selection.
>    * Selection results will be saved to `models/threshold_config.json`.
>
> 6. **Local Explanation Design:**
>    * For Logistic Regression: Local contribution = processed feature value $\times$ model coefficient.
>    * For Random Forest: A local evidence heuristic based on feature deviations from peer benchmarks (no SHAP unless installed; we will use a custom local heuristic).
>    * Local explanations will strictly separate: Observed Facts, Deterministic Derived Metrics, Model Predictions, and Local Contributions.
>
> 7. **Graceful Fallback:**
>    * If model artifacts are missing, scorer will output `scoring_mode = "rule_based_fallback"`, `model_prediction_available = false`, `risk_score_type = "heuristic"`, and `model_version = null` with a clear warning.

## Open Questions

> [!NOTE]
> None. The modeling constraints, files, structure, and metrics are fully aligned with the requested corrections.

---

## Proposed Changes

We will create/modify the following files strictly according to the approved repository structure:

### Component: Source Code (`src/cashflow_guardian/risk_engine/`)

#### [NEW] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/__init__.py)
Exports main interfaces: `score_cashflow_risk`, `load_risk_models`.

#### [NEW] [schemas.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/schemas.py)
Pydantic schemas for risk scoring input/output, feature vectors, explanation payloads, and fallback statuses.

#### [NEW] [model_loader.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/model_loader.py)
Handles joblib model loading, checking feature column lists against `feature_columns.json` and checking database health.

#### [NEW] [calibration.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/calibration.py)
Contains validation-set calibration utilities.

#### [NEW] [thresholds.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/thresholds.py)
Loads threshold config from `models/threshold_config.json` and assigns Low / Medium / High / Critical risk tiers based on risk scores and deterministic thresholds.

#### [NEW] [explanation.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/explanation.py)
Generates structured local explanations using coefficients and feature gaps, separating facts, predictions, and interpretations.

#### [NEW] [scoring.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/scoring.py)
Orchestrates loading features, scaling, scoring using the baseline/best model, and fallback heuristic processing.

#### [NEW] [monitoring.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/monitoring.py)
Implements logging and basic prediction logging.

---

### Component: Test Suite (`tests/`)

#### [NEW] [test_model_loader.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/risk_engine/test_model_loader.py)
Tests loading models, checking metadata/feature agreement, and fallback detection.

#### [NEW] [test_scoring.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/risk_engine/test_scoring.py)
Tests scoring under normal and fallback conditions. Includes leakage checks.

#### [NEW] [test_calibration.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/risk_engine/test_calibration.py)
Tests calibration outputs and Brier score validation.

#### [NEW] [test_explanation.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/risk_engine/test_explanation.py)
Tests explanation structure and benchmark comparison correctness.

#### [NEW] [test_thresholds.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/risk_engine/test_thresholds.py)
Tests mapping risk scores to correct Low / Medium / High / Critical tiers.

#### [NEW] [test_risk_engine_real_db.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/integration/test_risk_engine_real_db.py)
End-to-end integration test connecting to the read-only DuckDB source database, running a full scan and scoring.

---

### Component: Scripts (`scripts/`)

#### [NEW] [build_training_dataset.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/scripts/build_training_dataset.py)
Loads DuckDB tables, computes features in vectorized batch operations, appends candidate composite labels, runs consistency checks against single-business feature vector output, and saves to `models/training_dataset.parquet`.

#### [NEW] [train_risk_model.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/scripts/train_risk_model.py)
Performs train/val/test splits, fits preprocessing, trains Model A and Model B, applies validation-set calibration, computes thresholds, saves models to `models/`, and outputs detailed metrics.

#### [NEW] [validate_risk_engine.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/scripts/validate_risk_engine.py)
Validates the entire pipeline, checks for future data leaks, verifies refusal-to-score conditions, and runs consistency assertions.

---

## Verification Plan

### Leakage Tests (Hard Guards)
We will implement automated assertions in `tests/unit/risk_engine/test_scoring.py` and `scripts/validate_risk_engine.py` that raise a ValueError if:
1. Feature list contains a column with prefix `future_60d_`.
2. The Risk Engine scoring path tries to query or reference the `business_monthly_outcomes` table.
3. Preprocessing scaling is fit on validation or test sets.
4. Input parameters include transactions or snapshots after the specified `as_of_month`.

### Execution Flow
1. Run `python scripts/build_training_dataset.py` to build the training set and parquet file.
2. Run `python scripts/train_risk_model.py` to train, calibrate, select thresholds, and export models.
3. Run `pytest tests/unit/risk_engine/` and `pytest tests/integration/` to verify correctness.
4. Run `python scripts/validate_risk_engine.py` to generate the final validation report.
