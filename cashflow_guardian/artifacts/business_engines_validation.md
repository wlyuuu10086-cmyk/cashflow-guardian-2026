# Business Engines Validation Report

This report documents the validation results for the CashFlow Guardian Step 5 deterministic engines, structured tools, and database safety controls.

---

## 1. Database Immutability Verification

To guarantee that all analytics, scoring, and tools remain strictly read-only, we recorded and verified key properties of the source DuckDB database before and after running the entire test and validation suite.

### Database Attributes Comparison

| Attribute | Value Before Validation | Value After Validation | Mismatch |
| :--- | :--- | :--- | :---: |
| **File Modification Time** | `1783066679.5767782` | `1783066679.5767782` | **No** |
| **File Size (Bytes)** | `17,313,792` | `17,313,792` | **No** |
| **Table Count** | `13` | `13` | **No** |

### Verified Source Table Row Counts
*   `business_customers`: **1,500** rows
*   `bank_transactions`: **482,790** rows
*   `invoices`: **90,000** rows
*   `loans`: **2,800** rows
*   `repayments`: **46,790** rows
*   `payroll`: **36,000** rows
*   `business_monthly_snapshots`: **36,000** rows
*   `business_monthly_outcomes`: **36,000** rows
*   `credit_reviews`: **9,898** rows
*   `industry_benchmark`: **12** rows
*   `region_dim`: **5** rows
*   `region_macro_index`: **144** rows
*   `relationship_managers`: **60** rows

> [!NOTE]
> Database verification confirmed zero mutations. Zero temporary tables, views, or cache files were written back to the source DuckDB database file.

---

## 2. Test Execution Summary

A total of **31 unit and integration tests** were executed and passed successfully:
*   **Benchmark Engine Unit Tests:** 5 passed
*   **Scenario Engine Unit Tests:** 4 passed
*   **Intervention Engine Unit Tests:** 4 passed
*   **Model Loader Caching Unit Tests:** 4 passed
*   **Structured Tools Unit Tests:** 4 passed
*   **Risk Engine Unit Tests:** 6 passed (unrelated modules)
*   **Benchmark Engine Real DB Integration Tests:** 1 passed
*   **Scenario Engine Real DB Integration Tests:** 1 passed
*   **Tool Workflow Integration Tests:** 3 passed

All outputs were validated as JSON-serializable, and error boundaries were successfully verified to prevent the leakage of stack traces or absolute system paths.

---

## 3. Real Business Investigation Case: `B01395` (June 2025)

The business engines were validated against real client data dynamically extracted from the database.

### 3.1 Benchmark Gaps (Construction Services Sector)
The client was compared against a peer group of **30 peers** in the `Construction Services` industry and same revenue band:
*   **Cash-flow volatility:** Client value: **33,954.42** | Peer Median: **30,183.46** | Gap: **+3,770.96** | Direction: `similar`
*   **Average collection days:** Client value: **45.5 days** | Peer Median: **45.75 days** | Gap: **-0.25 days** | Direction: `similar`
*   **Late invoice rate:** Client value: **100%** | Peer Median: **100%** | Gap: **0.00** | Direction: `similar`
*   **Repayment burden ratio:** Client value: **489.0%** | Peer Median: **88.7%** | Gap: **+400.3%** | Direction: `worse`
*   **Payroll burden ratio:** Client value: **521.6%** | Peer Median: **180.4%** | Gap: **+341.2%** | Direction: `worse`
*   **Credit utilization:** Client value: **1.50** | Peer Median: **1.17** | Gap: **+0.33** | Direction: `worse`
*   **Overdraft days:** Client value: **16 days** | Peer Median: **10 days** | Gap: **+6 days** | Direction: `worse`
*   **Trend (3-month net cash flow):** Client value: **-20,804.28** | Peer Median: **-24,694.15** | Gap: **+3,889.87** | Direction: `better`

### 3.2 What-If Scenario Projections
*   **Baseline Risk Score:** **0.1012** (`AMBER` RAG status)
*   **No-Change Scenario Output:** Simulated Risk Score is **0.1012** (perfect baseline match, $\Delta = 0.000000$, verifying derived feature consistency).
*   **Downside Scenario (-20% Inflow, +10% Outflow, +15 Days Collection Delay):**
    *   Simulated Inflow: **0.00** (Baseline: **7,316.99**, with **28,165.68** deferred due to collection delays)
    *   Simulated Risk Score: **0.0870** (`GREEN`)
    *   Risk score change is labeled explicitly as a **model projection** and carries warnings clarifying that it is not an observed future outcome.

### 3.3 Draft Intervention Plan
*   **Plan Priority:** `MEDIUM`
*   **Evidence Triggers:** `['AMBER_RISK_TIER', 'HIGH_REPAYMENT_BURDEN', 'COLLECTION_DELAY_GAP', 'ACTIVE_OVERDRAFT', 'DECLINING_CASH_FLOW']`
*   **Human Approval Required:** `False` (no watchlist review was proposed)
*   **Recommended Action Playbook:**
    1.  `increase monitoring frequency`: Business is in the AMBER (medium risk) tier. Increase review frequency.
    2.  `request updated cash-flow information`: Request recent bank statements and cash flow projections to clarify stress signals.
    3.  `review repayment schedule`: Monthly scheduled repayments exceed 25% of cash inflows (Business value: 489.0%).
    4.  `verify large outstanding invoices`: Collection days are significantly higher than peer benchmarks (Business value: 45.5 days, Peer median: 45.8 days).
    5.  `assess short-term liquidity support eligibility`: Active overdraft days (16 days) detected in the current month.
*   **Prohibited Actions (Enforced Compliance):** Zero prohibited actions (like credit-limit reductions or payment freezes) were returned or suggested.
