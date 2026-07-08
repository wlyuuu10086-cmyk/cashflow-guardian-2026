# Comparative Label Audit: CashFlow Guardian

This document presents a comparative label audit evaluating four candidate target labels to establish a mathematically sound, observable, and leakage-free prediction target for the CashFlow Guardian early warning system.

---

## 1. Candidate Labels Evaluation Matrix

The following table summarizes the key properties of the four audited label candidates:

| Candidate Label | Mathematical Definition | Total Counts (0 / 1 / Null) | Avg. Pos Rate | Labeled Completeness | Actionable Event? | Sufficiently Discriminative? | Key Weakness |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Loan Delinquency** (`future_60d_dpd30_flag`) | $\mathbb{I}(\max_{h \in [T+1, T+2]} \text{days\_past\_due}_h > 30)$ | 32,154 / 846 / 3,000 | 2.56% | Complete up to Oct 2025 | Yes (credit default) | No (too sparse for early warning) | Misses liquidity stress if the client prioritizes debt service |
| **2. Collection Delay** (`future_60d_collection_delay_spike_flag`) | $\mathbb{I}(\text{avg\_days\_to\_pay} \text{ exceeds threshold in next 60d})$ | 29,182 / 3,818 / 3,000 | 11.57% | Complete up to Oct 2025 | Yes (operational delay) | Yes | Misses direct cash exhaustion and loan delinquency |
| **3. Combined Cash Stress** (`future_60d_cash_stress_observed`) | Precalculated union of delinquency, negative cash flow, and collection delay | 986 / 32,014 / 3,000 | 97.01% | Complete up to Oct 2025 | No | No (97% positive rate is non-discriminative) | Dominated by temporary net cash flow drops in synthetic data |
| **4. Proposed Composite Target** (`candidate_composite`) | $\text{dpd30\_flag} \lor (\text{neg\_cf\_flag} \land \text{collection\_delay\_flag})$ | 28,438 / 4,562 / 3,000 | 13.82% | Complete up to Oct 2025 | Yes (compound default/cash squeeze) | Yes (13.8% positive rate is well-balanced) | None; represents true structural distress |

---

## 2. Monthly Positive Rate Stability (Empirical Findings)

The monthly positive rates computed from the DuckDB database (excluding the truncated months `2025-11` and `2025-12`) are shown below:

| Month | Loan Delinquency (`dpd30`) | Collection Delay (`collection_delay`) | Combined Cash Stress (`cash_stress_observed`) | Proposed Composite Target (`candidate_composite`) |
| :--- | :---: | :---: | :---: | :---: |
| **2024-01** | 2.20% | 10.33% | 62.80% | 12.33% |
| **2024-02** | 2.00% | 13.40% | 84.87% | 15.07% |
| **2024-03** | 1.60% | 11.53% | 93.53% | 13.07% |
| **2024-04** | 1.53% | 11.67% | 98.20% | 13.07% |
| **2024-05** | 2.33% | 11.47% | 99.00% | 13.47% |
| **2024-06** | 2.93% | 11.80% | 99.27% | 14.53% |
| **2024-07** | 3.20% | 11.20% | 99.47% | 14.13% |
| **2024-08** | 3.33% | 10.00% | 99.73% | 12.93% |
| **2024-09** | 3.40% | 13.07% | 99.80% | 16.00% |
| **2024-10** | 3.40% | 11.27% | 99.80% | 14.33% |
| **2024-11** | 2.93% | 10.73% | 99.73% | 13.20% |
| **2024-12** | 2.73% | 10.27% | 99.80% | 12.73% |
| **2025-01** | 2.93% | 12.87% | 99.80% | 15.27% |
| **2025-02** | 3.00% | 14.73% | 100.00% | 17.27% |
| **2025-03** | 2.93% | 10.00% | 99.73% | 12.73% |
| **2025-04** | 2.93% | 12.13% | 99.87% | 14.73% |
| **2025-05** | 2.67% | 11.27% | 99.93% | 13.60% |
| **2025-06** | 2.80% | 12.93% | 99.67% | 15.47% |
| **2025-07** | 2.87% | 9.87% | 99.87% | 12.27% |
| **2025-08** | 1.80% | 10.53% | 99.87% | 12.13% |
| **2025-09** | 1.33% | 12.73% | 99.73% | 13.87% |
| **2025-10** | 1.53% | 10.73% | 99.80% | 11.93% |

---

## 3. Business Analysis & Interpretation of Candidates

### 1. Loan Delinquency Stress (`future_60d_dpd30_flag`)
* **Business Interpretation:** The customer experiences a severe credit event (payment delayed > 30 days) on an active loan within 60 days.
* **Weaknesses:** Highly sparse (2.56% of snapshots). If the model only targets DPD30, it fails to flag businesses experiencing early-stage liquidity constraints. Healthy businesses might prioritize paying their bank loans over suppliers, meaning they appear healthy in this flag until they suddenly default.

### 2. Collection Delay Stress (`future_60d_collection_delay_spike_flag`)
* **Business Interpretation:** The customer experiences a sudden rise in invoice collection times.
* **Weaknesses:** While collection delay is a key operational stress indicator, it does not necessarily translate into a credit default or insolvency if the firm maintains sufficient cash reserves.

### 3. Combined Cash Stress (`future_60d_cash_stress_observed`)
* **Business Interpretation:** The precalculated target in the database.
* **Weaknesses:** Non-discriminative. Because the synthetic database contains negative net cash flows in 97.8% of all snapshots, any flag that includes single negative cash flow months will label almost 97% of observations as stressed. A model trained on this target cannot distinguish between a temporary cash drawdown (e.g. inventory restocking) and actual structural distress.

### 4. Proposed Composite Target (`candidate_composite`)
* **Business Interpretation:** The customer experiences either:
  1. A credit default (`dpd30_flag == 1`), **OR**
  2. A joint liquidity squeeze: negative cash flow **AND** severe collection delay.
* **Weaknesses:** It does not capture isolated negative cash flow events (which are noise in this database).
* **Rationale:** A business with negative cash flow that *also* cannot collect its invoices in time is under severe distress, as it cannot rely on short-term receivables to cover its cash deficit. This compound indicator avoids synthetic noise while capturing genuine liquidity distress and credit default risks.

---

## 4. Final Recommendation & MVP Selection

We select **Candidate 4: Proposed Composite Target (`candidate_composite`)** as the primary modeling target.
* **Empirical Advantage:** It provides a balanced distribution (13.82% positive rate) that is extremely stable over time, making it highly discriminative for training both Logistic Regression and RandomForest models.
* **Business Soundness:** It captures both the final credit failure state and the early-warning liquidity squeeze state, aligning perfectly with early risk intervention objectives.
