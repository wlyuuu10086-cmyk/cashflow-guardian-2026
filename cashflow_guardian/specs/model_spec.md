# Model Specification: CashFlow Guardian

This document defines the requirements, target labels, features, modeling strategies, validation metrics, and guardrails for the **CashFlow Guardian** early-warning risk models.

---

## 1. Target-Label Definition & Audit Requirements

The primary goal of the model is to predict **SME Cash Flow Stress within the next 60 days**. 

### 1.1 Candidate Label Definitions for Evaluation
We audit and compare the following candidate labels from the synthetic database to select the optimal target:
1. **Candidate 1: Default/Delinquency Stress (`future_60d_dpd30_flag`)**
   * *Definition:* The customer incurs a loan repayment delay exceeding 30 Days Past Due (`days_past_due > 30`) within the next 60 days.
   * *Assessment:* Very high credit relevance, but potentially sparse in early stages of stress.
2. **Candidate 2: Liquidity Stress (`future_60d_negative_cashflow_flag`)**
   * *Definition:* The customer records negative net cash flow (`net_cash_flow < 0`) in the next 60 days.
   * *Assessment:* Frequent, but high noise (many healthy firms temporarily experience negative net cash flows due to investment or inventory cycles).
3. **Candidate 3: Combined Cash Stress (`future_60d_cash_stress_observed` - Selected)**
   * *Definition:* A compound flag representing any of: 30+ DPD loan payment, persistent negative cash flow leading to critical balance depletion, or severe collection delay spikes.
   * *Assessment:* Captures multiple dimensions of business stress. **This is the target label selected for the MVP.**

### 1.2 Dataset Boundary Audit
> [!IMPORTANT]
> **Boundary Label Truncation:**
> The synthetic dataset ends on `2025-12`. Because the outcome labels require a forward-looking window of 60 days, rows for the months **`2025-11` and `2025-12` have incomplete/NULL labels**.
> * **Mandatory Action:** The modeling pipeline must exclude all snapshots with `month >= '2025-11'` from the training, validation, and test datasets.
> * **No Imputation:** These outcomes must never be imputed or filled with zeros; they must be dropped during training set generation to prevent severe label corruption.

---

## 2. Point-in-Time Feature Policy & Excluded Columns

### 2.1 Point-in-Time Feature Policy
All model features must be generated strictly from data available **on or before month $T$** when predicting outcomes in month $T+1$ and $T+2$:
* Features are calculated using aggregations (rolling 3-month averages, 6-month volatility) over $T, T-1, T-2$, etc.
* **Leakage Guard:** The outcome table `business_monthly_outcomes` is strictly isolated. No query inside the training feature generator or inference engine may join or reference this table except to append labels during the offline training split.

### 2.2 Excluded Columns
The following columns must be explicitly excluded from the model's feature set:
* `future_60d_dpd30_flag` (Direct lookahead target)
* `future_60d_negative_cashflow_flag` (Direct lookahead target)
* `future_60d_collection_delay_spike_flag` (Direct lookahead target)
* `future_60d_cash_stress_observed` (Direct lookahead target)
* `business_name` (Identifiers leading to memorization)
* `relationship_manager_id` (Bias risk)
* `onboarding_date` (Leakage risk if not parsed into relative age)

---

## 3. Chronological Validation Strategy

To simulate real-world deployment, random K-fold cross-validation is prohibited. We enforce a **chronological time-series split** (rolling window train/test splits):

* **Train Set:** Data from `2024-01` to `2025-04` (16 months of historical observations).
* **Validation Set:** Data from `2025-05` to `2025-07` (3 months). Used to tune hyperparameters, calibrate probabilities, and draft candidate thresholds.
* **Test Set (Holdout):** Data from `2025-08` to `2025-10` (3 months). Capped at October due to the 60-day boundary truncation.

---

## 4. Model Architectures (Baseline vs. Candidate)

### 4.1 Mandatory Baseline Model
* **Algorithm:** Logistic Regression (L2 regularized).
* **Implementation:** `sklearn.linear_model.LogisticRegression`.
* **Purpose:** Serves as a simple, highly interpretable linear baseline. 

### 4.2 Candidate Production Model
* **Algorithm:** XGBoost Classifier.
* **Implementation:** `xgboost.XGBClassifier`.
* **Purpose:** Captures non-linear feature interactions (e.g., interaction between high repayment burden and drop in cash inflows) and handles outlier transactions robustly.
* **Constraint:** No other tree-based candidate (like LightGBM) is required or implemented for the MVP to keep execution overhead minimal.

---

## 5. Model Evaluation Metrics

No final metric values are defined in this specification, as no model has been trained. The evaluation pipeline must compute and report all of the following metrics on the holdout test set:

1. **Area Under the Precision-Recall Curve (PR-AUC):**
   * *Why:* Cash-flow stress is highly imbalanced (few businesses fail). PR-AUC is more informative than ROC-AUC or Accuracy for highly skewed labels.
2. **Recall (Sensitivity):**
   * *Why:* Missing a stressed business (false negative) is far costlier to the bank than a false alarm. We target high recall (e.g., capturing >85% of stressed businesses).
3. **Precision (Positive Predictive Value):**
   * *Why:* Low precision results in excessive false alarms, overwhelming RM team review capacity.
4. **Probability Calibration (Brier Score):**
   * *Why:* The risk score must represent a true probability. If a model scores a business as 80% risk, approximately 8 out of 10 such businesses should experience stress. We evaluate calibration using calibration curves (reliability diagrams) and Brier scores.
5. **Top-Risk Capture (Capture Rate in Top 10%):**
   * *Why:* RMs have limited capacity. We measure the percentage of actual stressed businesses captured within the top 10% highest-scoring businesses.

---

## 6. Threshold Selection Framework

Final scoring thresholds are not hardcoded. They must be selected dynamically using the validation set based on:
1. **Operational Capacity:** The maximum number of alerts the Portfolio Monitoring Team can investigate monthly (e.g., capping Red alerts at 5% of the portfolio).
2. **Cost Optimization:** Weighing the financial cost of a write-off (false negative) against the administrative cost of a credit review (false positive).
3. **RAG Tiers Classification (Provisional Defaults):**
   * **Red (High Risk):** Actionable alerts with high probability of stress. Requires manual review.
   * **Amber (Medium Risk):** Watchlist candidate; requires automated monitoring.
   * **Green (Low Risk):** Healthy business; no action.

---

## 7. Refusal-to-Score Guardrails

The model scoring tool `score_cashflow_risk` must immediately refuse to score a business and return a fallback warning under the following conditions:
* The business is not registered in `business_customers` (Invalid ID).
* The business has less than 3 months of snapshots (`has_sufficient_history == false`).
* The requested scoring month has major transaction gaps indicating lack of core data integration.
* The requested month is outside the range `2024-01` to `2025-12`.
