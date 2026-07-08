# Data Engine Integration Validation Report

This report summarizes the validation results of the P0 read-only **Data Engine** for the **CashFlow Guardian** platform.

## 1. Database Immutability Check

We captured and verified that the source database remains completely pristine and unmodified before and after running the test suite and validation scripts.

| Metric | Before Execution | After Execution | Status |
| :--- | :--- | :--- | :---: |
| **File Modification Time** | `1783066679.5767782` | `1783066679.5767782` | **UNCHANGED** |
| **`business_customers`** | `1,500` rows | `1,500` rows | **UNCHANGED** |
| **`bank_transactions`** | `482,790` rows | `482,790` rows | **UNCHANGED** |
| **`invoices`** | `90,000` rows | `90,000` rows | **UNCHANGED** |
| **`loans`** | `2,800` rows | `2,800` rows | **UNCHANGED** |
| **`repayments`** | `46,790` rows | `46,790` rows | **UNCHANGED** |
| **`payroll`** | `36,000` rows | `36,000` rows | **UNCHANGED** |
| **`business_monthly_snapshots`** | `36,000` rows | `36,000` rows | **UNCHANGED** |
| **`industry_benchmark`** | `12` rows | `12` rows | **UNCHANGED** |

**Conclusion:** The read-only connection pool and safety guards successfully protected the database from any modification.

---

## 2. Actual Verified Database Schema

We verified the layout and types of the three core tables:

### Table: `business_customers`
*   `business_id` (VARCHAR) - Primary Key. Real format is `B\d{5}` (e.g., `B00001`).
*   `business_name` (VARCHAR)
*   `industry` (VARCHAR)
*   `region` (VARCHAR)
*   `revenue_band` (VARCHAR)
*   `relationship_manager_id` (VARCHAR)
*   `onboarding_date` (DATE)

### Table: `business_monthly_snapshots`
*   `business_id` (VARCHAR)
*   `month` (VARCHAR) - format `YYYY-MM`. Min: `2024-01`, Max: `2025-12`.
*   `opening_cash_balance_proxy` (DOUBLE)
*   `ending_cash_balance_proxy` (DOUBLE)
*   `avg_daily_balance_proxy` (DOUBLE)
*   `overdraft_days_proxy` (INTEGER)
*   `cash_inflow_observed` (DOUBLE)
*   `cash_outflow_observed` (DOUBLE)
*   `net_cash_flow_observed` (DOUBLE)
*   `avg_days_to_pay` (DOUBLE)
*   `late_invoice_rate` (DOUBLE)
*   `payroll_amount` (DOUBLE)
*   `employee_count` (INTEGER)
*   `scheduled_debt_service` (DOUBLE)
*   `actual_debt_service` (DOUBLE)
*   `max_dpd` (INTEGER)
*   `available_credit_drawn_ratio` (DOUBLE)

### Table: `industry_benchmark`
*   `industry_id` (VARCHAR)
*   `industry` (VARCHAR)
*   `benchmark_margin` (DECIMAL(3,2))
*   `benchmark_cash_flow_volatility` (DECIMAL(3,2))
*   `benchmark_collection_days` (INTEGER)
*   `benchmark_repayment_burden_pct` (INTEGER)
*   `payroll_intensity` (DECIMAL(3,2))

---

## 3. Selected Real Test Inputs
*   **Valid Business ID:** `B00001`
*   **Valid As-Of Month:** `2025-06`
*   **Invalid Business ID:** `B99999`
*   **Latest Boundary Month:** `2025-12` (Incomplete outcomes)

---

## 4. Run Summaries

### 4.1 Database Health Result
*   `database_available`: `True`
*   `read_only`: `True` (Verified: `CREATE TABLE` and `INSERT` statements fail natively at connection level).
*   `required_tables_present`: `True`
*   `missing_tables`: `[]`

### 4.2 Data-Quality Result (`B00001`, `2025-06`)
*   `status`: `COMPLETED`
*   `can_build_features`: `True`
*   `errors`: `[]`
*   `warnings`: `[]`
*   `provenance.future_data_used`: `False`

### 4.3 Business-History Result Summary (`B00001`, `2025-06`)
*   **Retrieved Months:** `6` (Months: `2025-01` to `2025-06` inclusive)
*   **Latest Month Metrics (`2025-06`):**
    *   Cash Inflow: `$23,358.69`
    *   Ending Balance: `-$1,257,853.73`
*   **Provenance:**
    *   `source_tables`: `['business_monthly_snapshots']`
    *   `future_data_used`: `False`

### 4.4 Portfolio-Snapshot Summary (`2025-06`)
*   **Records Returned:** `5` (when limited to 5 for validation script)
*   **Sample Record:** Business ID `B00001`, Name `"Business 00001"`, Data Quality Status `COMPLETED`.
*   **Provenance:**
    *   `source_tables`: `['business_monthly_snapshots', 'business_customers']`
    *   `future_data_used`: `False`

### 4.5 Peer-Benchmark Summary (`B00001`, `2025-06`)
*   **Industry Segment:** `E-commerce Sellers`
*   **Business Margin:** `-3.6103` (representing net_cash_flow / inflow)
*   **Benchmark Margin:** `0.3300`
*   **Margin Delta:** `-3.9403` (Business is under-performing benchmark by 394%)
*   **Collection Days Delta:** `-1.0` days (Business collects payments 1 day faster than peers)

### 4.6 Point-in-Time Feature Summary (`B00001`, `2025-06`)
*   **Feature Vector Length:** `30`
*   **Features Computed:** Includes current month metrics, rolling 3-month averages, 3-month/6-month net cash flow volatilities, MoM changes, 3-month changes (inflow, collection days, repayment burden), and industry benchmark gaps.
*   **Lookahead Prevention:** `future_data_used` flag is `False`. The query used temporal filters restricting all data to `month <= '2025-06'`.

---

## 5. Security & Input Rejections

### 5.1 Invalid Business ID Handling
*   Inputting `"B99999"` throws a typed `BusinessIDNotFoundError` stating: `Business ID 'B99999' was not found in the database.`
*   Inputting SQL injection characters (e.g. `B00001; DROP TABLE business_customers;`) is intercepted by the validators and throws a `ValidationError` blocking any database execution.

### 5.2 Boundary Month Handling
*   Querying the latest month `2025-12` returns `status = COMPLETED` and `can_build_features = True`.
*   The system operates correctly at the boundaries, pulling all available records up to `2025-12` without leaking or lookahead, setting `future_data_used = False`.

### 5.3 Attempted Source Write Rejection
*   Any query containing prohibited write commands like `INSERT`, `UPDATE`, or `DROP` triggers a connection block or catches a `DatabaseWriteError` from the safety guard.
*   Furthermore, the DuckDB file is attached with `read_only=True`, so write queries fail natively with a `ConnectionException`.

---

## 6. Known Limitations

1.  **Read-Only Boundary:** The Data Engine cannot register watchlist actions directly into the DuckDB database. These actions must be stored in a separate local write-store (`data/demo_actions.json`).
2.  **Inference Scope:** The Data Engine does not perform risk scoring or model loading; it is restricted to data extraction, quality verification, and feature calculations.
3.  **Boundary Month Outcome Labels:** Labels in `business_monthly_outcomes` for `2025-11` and `2025-12` are incomplete (NULL) due to the 60-day target window truncation. The data engine handles retrieval normally, but downstream model training must exclude these months to prevent target corruption.
