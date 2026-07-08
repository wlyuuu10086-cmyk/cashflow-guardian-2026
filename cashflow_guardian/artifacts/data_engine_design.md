# Data Engine Design Document

This document records the verified database schemas, point-in-time leakage prevention design, validation strategies, and connection rules for the **CashFlow Guardian** Data Engine.

## 1. Verified DuckDB Database Schema

We verified the schemas and row counts directly from `sme_cashflow_stress.duckdb`.

### 1.1 Core Tables

#### Table: `business_customers` (1,500 rows)
Represents the grain of a unique SME business customer.
- `business_id` (VARCHAR) - Unique identifier. Real format is `B\d{5}` (e.g., `B00001` to `B01500`).
- `business_name` (VARCHAR)
- `industry_id` (VARCHAR)
- `industry` (VARCHAR)
- `region_id` (VARCHAR)
- `region` (VARCHAR)
- `state` (VARCHAR)
- `city_tier` (VARCHAR)
- `years_in_business` (INTEGER)
- `revenue_band` (VARCHAR)
- `estimated_monthly_revenue_band_midpoint` (INTEGER)
- `employee_count_base` (INTEGER)
- `legal_structure` (VARCHAR)
- `credit_score_band_at_origination` (VARCHAR)
- `has_prior_delinquency` (INTEGER)
- `owner_experience_years` (INTEGER)
- `online_sales_share` (DOUBLE)
- `relationship_manager_id` (VARCHAR)
- `onboarding_date` (DATE)
- `primary_bank_account_type` (VARCHAR)

#### Table: `business_monthly_snapshots` (36,000 rows)
Holds monthly pre-aggregated financial snapshots for 24 months.
- `business_id` (VARCHAR)
- `month` (VARCHAR) - format `YYYY-MM`. Min month: `'2024-01'`, Max month: `'2025-12'`.
- `month_start_date` (DATE)
- `opening_cash_balance_proxy` (DOUBLE)
- `ending_cash_balance_proxy` (DOUBLE)
- `avg_daily_balance_proxy` (DOUBLE)
- `overdraft_days_proxy` (INTEGER)
- `transaction_count` (BIGINT)
- `cash_inflow_observed` (DOUBLE)
- `cash_outflow_observed` (DOUBLE)
- `net_cash_flow_observed` (DOUBLE)
- `invoice_count` (BIGINT)
- `invoice_amount_total` (DOUBLE)
- `avg_days_to_pay` (DOUBLE)
- `late_invoice_rate` (DOUBLE)
- `payroll_amount` (DOUBLE)
- `employee_count` (INTEGER)
- `scheduled_debt_service` (DOUBLE)
- `actual_debt_service` (DOUBLE)
- `max_dpd` (INTEGER)
- `available_credit_drawn_ratio` (DOUBLE)

#### Table: `industry_benchmark` (12 rows)
Provides peer benchmarks for each industry.
- `industry_id` (VARCHAR)
- `industry` (VARCHAR)
- `benchmark_margin` (DECIMAL(3,2))
- `benchmark_cash_flow_volatility` (DECIMAL(3,2))
- `benchmark_collection_days` (INTEGER)
- `benchmark_repayment_burden_pct` (INTEGER)
- `payroll_intensity` (DECIMAL(3,2))
- `seasonality_peak_month` (INTEGER)
- `typical_transaction_intensity` (DECIMAL(2,1))
- `economic_sensitivity` (DECIMAL(3,2))

### 1.2 Other Tables
- `bank_transactions` (482,790 rows): Grain of transaction.
- `invoices` (90,000 rows): Grain of invoice.
- `loans` (2,800 rows): Grain of loan.
- `repayments` (46,790 rows): Grain of repayment.
- `payroll` (36,000 rows): Grain of payroll.
- `credit_reviews` (9,898 rows): Credit actions.
- `region_dim` (5 rows): Region dimension metadata.
- `region_macro_index` (144 rows): Macro indices.
- `relationship_managers` (60 rows): Portfolio owners.

---

## 2. Dynamic Input Validation Strategy

### 2.1 Business ID Validation
*   **Real Format:** The real database has IDs in `B\d{5}` format. However, some mocks or tests might use `BUS_\d{3,4}`.
*   **Authoritative Rule:** Check if the ID exists in the database `business_customers` table.
*   **Pattern Rule:** We will validate that the input matches either the real database pattern `^B\d{5}$` or `^BUS_\d{3,4}$`, but the authoritative check is **existence**.

### 2.2 Month Validation
*   **Dynamic Bounds:** We query the database at startup/health check to find the minimum and maximum month in `business_monthly_snapshots` table.
*   **Format:** `YYYY-MM`.
*   **Validation:** Verify format via regex, and ensure that the month lies between the dynamically queried `min_month` and `max_month` (inclusive).

---

## 3. Point-in-Time Leakage Prevention Design

To avoid lookahead bias during inference:
1.  **Isolation of outcomes:** The `business_monthly_outcomes` table must never be queried or joined for inference.
2.  **No Future outcomes columns:** Features and outputs must not reference `future_60d_*` fields.
3.  **Validation Guard:** The connection execution layer will inspect all SQL statements before running. If a query contains the strings `"business_monthly_outcomes"` or `"future_60d_"` (case-insensitive), execution will be blocked and a `QuerySafetyError` raised.
4.  **Temporal Filtering:** Queries must bind the month to less than or equal to `as_of_month` (e.g. `month <= ?` or `transaction_month <= ?`).

---

## 4. Read-Only Connection Policy

- Open connection with `read_only=True`:
  ```python
  conn = duckdb.connect(database_path, read_only=True)
  ```
- This forces DuckDB to throw an exception on write operations. We catch this and throw a `DatabaseWriteError`.
