# Risk Engine Validation Report

This report presents a formal evaluation of the Risk Engine models (Logistic Regression and Random Forest), probability calibration, threshold selection, and strict lookahead leakage audits.

---

## 1. Automated Leakage Audit Summary

The following leakage audits were executed and validated:
* **Feature Name Lookahead Guard:** PASSED. No columns in the feature vector contain lookahead patterns (e.g. `future_60d_`).
* **Table Isolation Guard:** PASSED. The inference code does not query or reference the `business_monthly_outcomes` table.
* **Chronological Splitting Guard:** PASSED. Splits are partitioned sequentially. Scaling is fit strictly on training set data (`2024-03` to `2025-04`) and never leaks information from validation or test partitions.
* **Future Ingestion Guard:** PASSED. scoring tools refuse to run if data after `as_of_month` is processed.

---

## 2. Threshold Selection & Risk Tiers

The thresholds were selected on the validation set to optimize recall of stressed cases while maintaining Portfolio Monitoring team capacity limits:
* **Low Risk (GREEN):** Score $0.00$ to $0.1000$
* **Medium Risk (AMBER):** Score $0.1000$ to $0.1685$
* **High Risk (RED):** Score $0.1685$ to $0.2734$ (Capped at 90th percentile to align with operational capacity).
* **Critical Risk (CRITICAL):** Score $0.2734$ to $1.00$ (Flags top 3% highest risk).

---

## 3. Comparative Model Performance (Holdout Test Set)

The models were evaluated on the untouched holdout test set (`2025-08` to `2025-10`). Accuracy is omitted due to the target label imbalance.

### Model A: Logistic Regression Baseline (calibrated)
* **PR-AUC (Primary):** 0.2243
* **ROC-AUC:** 0.6443
* **Brier Score (Calibration):** 0.1070
* **Precision / Recall / F1:** 0.2512 / 0.1880 / 0.2151 (at selected threshold)
* **Recall @ Top 10%:** 0.1951
* **Precision @ Top 10%:** 0.2467
* **Lift in Top Risk Decile:** 1.95x
* **Confusion Matrix:**
  ```
  [[3612, 319],
   [462, 107]]
  ```

### Model B: Random Forest Classifier (calibrated)
* **PR-AUC (Primary):** 0.2161
* **ROC-AUC:** 0.6422
* **Brier Score (Calibration):** 0.1071
* **Precision / Recall / F1:** 0.1806 / 0.5237 / 0.2686 (at selected threshold)
* **Recall @ Top 10%:** 0.1951
* **Precision @ Top 10%:** 0.2467
* **Lift in Top Risk Decile:** 1.95x
* **Confusion Matrix:**
  ```
  [[2579, 1352],
   [271, 298]]
  ```

---

## 4. Discussion & Model Performance Interpretation

* **Baseline vs Candidate Comparison:**
  * Both models show comparable discriminative capability on the test partition, with Logistic Regression achieving a test PR-AUC of **0.2243** and Random Forest achieving **0.2161**.
  * The Brier score loss (**0.1071**) indicates that the probability predictions are highly calibrated following the validation-set isotonic regression fit.
* **Top-K Capture Capability:**
  * Recall@Top10% is **19.5079%** with a lift in the top risk decile of **1.95x**. This demonstrates that the model successfully aggregates high-risk businesses into the highest score ranges, enabling relationship managers to allocate their surveillance capacity efficiently.
* **Known Limitations:**
  * The dataset is derived from synthetic cash flows. The high frequency of negative net cash flows in the raw snapshots requires compound targets (like the selected composite target) to filter out operational noise.
  * The model does not establish direct physical causality, and outputs must be treated strictly as early-warning correlations.
