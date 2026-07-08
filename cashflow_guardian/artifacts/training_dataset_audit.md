# Training Dataset Audit Report

This report documents the validation, exclusions, split row counts, and class prevalence of the batch-built training dataset.

---

## 1. Dataset Construction Summary

* **Database Source:** `sme_cashflow_stress.duckdb`
* **Total Raw Snapshot Records:** 36,000
* **Exclusions Applied:**
  * **Boundary Months Truncation:** 3,000 records (months `2025-11` and `2025-12` excluded due to incomplete outcomes).
  * **Insufficient History Length:** 3,000 records (first 2 months `2024-01` and `2024-02` for all businesses excluded since history count < 3).
* **Final Labeled Modeling Records:** 30,000

---

## 2. Selected Target Label Characterization

* **MVP Target Column:** `candidate_composite`
* **Mathematical Definition:**
  $$\text{Target}_{i, t} = \text{future\_60d\_dpd30\_flag} == 1 \lor (\text{future\_60d\_negative\_cashflow\_flag} == 1 \land \text{future\_60d\_collection\_delay\_spike\_flag} == 1)$$
* **Business Interpretation:** The customer experiences a credit default (loan delay > 30 days) OR a combined liquidity crisis (negative net cash flow AND severe collection delays).
* **Overall Prevalence:** 13.84% (Positives: 4,151, Negatives: 25,849)

---

## 3. Chronological Split Prevalence and Counts

The final dataset is split chronologically into Train, Validation, and Test sets:

| Split Partition | Period Range | Total Rows | Positive Cases | Negative Cases | Positive Class Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Train Set** | `2024-03` to `2025-04` | 21,000 | 2,962 | 18,038 | 14.10% |
| **Validation Set** | `2025-05` to `2025-07` | 4,500 | 620 | 3,880 | 13.78% |
| **Test Set (Holdout)** | `2025-08` to `2025-10` | 4,500 | 569 | 3,931 | 12.64% |

> [!IMPORTANT]
> **Splits Verification:**
> * All splits have both classes present.
> * Positive class rates remain stable between 12.64% and 14.10% across the time-series split.
> * No leakage occurs since splits are strictly sequential and divided by month.

---

## 4. Missingness and Feature Quality Report

A missingness check on the final training features indicates:
* **Numeric Features Missingness:** 0.00% missing values (due to rolling mean imputation/fallback defaults within the Data Engine's logic).
* **Categorical Features Missingness:** 0.00% missing values in `industry`, `region`, `revenue_band`, and `legal_structure`.
* **Consistency Check Status:** 100% matched against the single-business Data Engine feature builders.
