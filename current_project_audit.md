# SME Cash Flow Stress Early Warning System - Project Inventory & Audit Report

This report contains a comprehensive inventory and audit of the current analytics project. It reviews the directory structure, table schemas, project completion status, potential risks, and outlines a recommended migration plan to transition the existing analytics sandbox into **CashFlow Guardian**—a production-grade, agent-augmented risk monitoring and intervention system.

---

## 1. Project Folder Structure

The project directory is structured as follows:

```text
d:\5-Days-AI-Kaggle\Capstone
└── cashflow_guardian
    └── sme_cashflow_stress_project
        ├── README.md
        ├── data/
        │   ├── dataset_summary.json
        │   ├── row_counts.csv
        │   ├── sme_cashflow_stress.duckdb
        │   └── csv/
        │       ├── bank_transactions.csv
        │       ├── business_customers.csv
        │       ├── business_monthly_outcomes.csv
        │       ├── business_monthly_snapshots.csv
        │       ├── calendar_months.csv
        │       ├── credit_reviews.csv
        │       ├── industry_benchmark.csv
        │       ├── invoices.csv
        │       ├── loans.csv
        │       ├── payroll.csv
        │       ├── region_macro_index.csv
        │       ├── relationship_managers.csv
        │       └── repayments.csv
        ├── docs/
        │   ├── data_dictionary.csv
        │   ├── project_brief.md
        │   └── week_plan.md
        ├── notebooks/
        │   └── 01_starter_analysis.ipynb
        ├── sql/
        │   ├── 01_data_overview.sql
        │   ├── 02_cashflow_metric_baseline.sql
        │   └── 03_modeling_dataset_template.sql
        └── src/
            └── starter_framework.py
```

---

## 2. File-by-File Inventory

| File | Relative Path | Purpose / Description |
| :--- | :--- | :--- |
| [README.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/README.md) | `README.md` | General overview of the starter package. Documents database path suggestions (specifically Colab vs. Local), core table summaries, project description, and run guidelines. |
| [dataset_summary.json](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/data/dataset_summary.json) | `data/dataset_summary.json` | Stores metadata about the synthetic dataset generation, including the random seed, date ranges (`2024-01` to `2025-12`), number of businesses (`1500`), total row counts, and table-level row allocations. |
| [row_counts.csv](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/data/row_counts.csv) | `data/row_counts.csv` | A generated file listing row and column counts for each major table in the synthetic database. |
| [sme_cashflow_stress.duckdb](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/data/sme_cashflow_stress.duckdb) | `data/sme_cashflow_stress.duckdb` | The core database file. It contains 14 local tables and views, providing transactional, financial, and macro data for analytical and modeling tasks. |
| Raw CSV Files | `data/csv/*.csv` | Thirteen source CSV files corresponding to the database tables. These serve as a backup/source data and can be used to rebuild the DuckDB file if needed. |
| [data_dictionary.csv](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/docs/data_dictionary.csv) | `docs/data_dictionary.csv` | Full definition mapping of all tables and columns including description, data type, and context. |
| [project_brief.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/docs/project_brief.md) | `docs/project_brief.md` | Business positioning documentation outlining commercial banking context, objectives, and six core business questions. |
| [week_plan.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/docs/week_plan.md) | `docs/week_plan.md` | The syllabus/curriculum for the original 8-week internship project, specifying weekly deliverables and focus areas. |
| [01_starter_analysis.ipynb](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/notebooks/01_starter_analysis.ipynb) | `notebooks/01_starter_analysis.ipynb` | Minimal Jupyter Notebook demonstrating connection to the database and basic table count verification. |
| [01_data_overview.sql](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/sql/01_data_overview.sql) | `sql/01_data_overview.sql` | SQL template to query basic stats, industry/region counts, and repayment statistics in DuckDB. |
| [02_cashflow_metric_baseline.sql](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/sql/02_cashflow_metric_baseline.sql) | `sql/02_cashflow_metric_baseline.sql` | Baseline query aggregating cash inflow/outflow, scheduled payments, invoice lag, payroll, and debt/payroll burden ratios. |
| [03_modeling_dataset_template.sql](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/sql/03_modeling_dataset_template.sql) | `sql/03_modeling_dataset_template.sql` | SQL template detailing feature engineering formulas (rolling averages, volatility, changes) and mapping future target labels. |
| [starter_framework.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/src/starter_framework.py) | `src/starter_framework.py` | A basic Python execution script that verifies DuckDB connectivity, lists tables, and prints row counts. |

---

## 3. Project Completeness Analysis (8-Week Curriculum View)

The week-by-week curriculum specified in [week_plan.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/docs/week_plan.md) has been cross-referenced with the current code and documentation.

| Week | Phase | Expected Deliverables | Current Status | Notes & Gaps |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Business Understanding and Metric Design | Background summary and core metric list | **Completed** | Defined in [project_brief.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/docs/project_brief.md) and SQL metrics baseline formulas. |
| **2** | Data Cleaning and Integration | Data dictionary, SQL cleaning scripts, analytical wide table | **Partially Completed** | Data dictionary exists. The raw tables are integrated in DuckDB. However, **no data cleaning scripts** or **persistent analytical wide tables** exist. |
| **3** | Cash Flow Metric Analysis | Cash inflow/outflow, net cash flow, volatility, burden ratios | **Barely Started** | A SQL baseline query template is provided in `02_cashflow_metric_baseline.sql`, but **no actual analysis, visualization, or tables** are constructed. |
| **4** | Industry Benchmarking and Risk Signal Identification | Benchmark analysis and early warning signals | **Barely Started** | Benchmarks exist in the `industry_benchmark` table, but **no logic or analysis** has been built to benchmark customer data against them. |
| **5** | Feature Engineering and Label Construction | Modeling dataset generation | **Partially Completed** | Formula definitions exist in `03_modeling_dataset_template.sql` but **no modeling dataset has been generated or stored**. |
| **6** | Machine Learning Modeling | Model training, validation, results, and feature importance | **Missing / Not Started** | **No modeling scripts**, pipeline files, trained models, or feature importance reports exist. |
| **7** | Dashboard and Strategy Design | Dashboard interface and early warning list | **Missing / Not Started** | **No UI, streamlit code, dashboard screens**, or structured risk intervention strategies. |
| **8** | Final Report and Presentation | Final report, business recommendations, resume bullets | **Missing / Not Started** | **No final deliverables**, reports, summaries, or slides exist. |

---

## 4. Incomplete, Placeholder, or Missing Elements

> [!WARNING]
> While the repository has a solid data structure and initial SQL ideas, it is currently an **empty shell** with respect to actual processing logic, modeling pipelines, and production features.

### Incomplete/Placeholder Elements:
*   **Jupyter Notebook:** `01_starter_analysis.ipynb` contains a single execution cell that runs a basic row-count query. It is a starter template.
*   **Starter Script:** `starter_framework.py` is a simple database connection tester, not a modular framework.
*   **SQL Queries:** The files in the `sql/` directory are raw text queries. They are not parameterized or automated, and their outputs are not saved to any destination tables.

### Missing Critical Elements:
*   **Data Pipelines & ETL:** No Python or dbt scripts to handle pipeline stages (cleaning, transformations, loading).
*   **Feature Store / Tables:** No analytical wide tables built inside the database to serve as the unified feature source.
*   **ML Pipeline:** No Python scripts for model training, cross-validation (time-series split), hyperparameter tuning, model saving, or inference.
*   **Agentic Orchestration:** No code for an LLM-based agent or explanation system to detail risk factors and playbooks.
*   **Dashboard / UI:** No dashboard files or Streamlit application.
*   **Deployment Configuration:** No dependency manifest (`requirements.txt` or `pyproject.toml`) or setup files.

---

## 5. DuckDB Database Tables & Schemas

The database file `data/sme_cashflow_stress.duckdb` contains **14 tables and views** representing 742,018 rows of synthetic data.

### Table: `business_customers`
*Grain: Business (1,500 rows)*
*   `business_id` (VARCHAR): Unique business customer ID.
*   `business_name` (VARCHAR): Synthetic business name.
*   `industry_id` (VARCHAR): Link to benchmarks.
*   `industry` (VARCHAR): High-level industry sector.
*   `region_id` (VARCHAR): Link to geographic data.
*   `region` (VARCHAR): Region description.
*   `state` (VARCHAR): US State.
*   `city_tier` (VARCHAR): Tier 1/2/3 categorization.
*   `years_in_business` (INTEGER): Operating age.
*   `revenue_band` (VARCHAR): Estimated annual revenue range.
*   `estimated_monthly_revenue_band_midpoint` (INTEGER): Revenue proxy.
*   `employee_count_base` (INTEGER): Base employee headcount.
*   `legal_structure` (VARCHAR): LLC, Corporation, Sole Proprietorship, etc.
*   `credit_score_band_at_origination` (VARCHAR): Credit score tier.
*   `has_prior_delinquency` (INTEGER): Indicator (0/1).
*   `owner_experience_years` (INTEGER): Managerial experience.
*   `online_sales_share` (DOUBLE): Percentage of online revenue.
*   `relationship_manager_id` (VARCHAR): Linked relationship manager.
*   `onboarding_date` (DATE): Onboarding date.
*   `primary_bank_account_type` (VARCHAR): Operating, savings, etc.

### Table: `bank_transactions`
*Grain: Transaction (482,790 rows)*
*   `transaction_id` (VARCHAR): Unique transaction identifier.
*   `business_id` (VARCHAR): Linked business ID.
*   `transaction_date` (DATE): Date of transaction.
*   `transaction_month` (VARCHAR): Month format `YYYY-MM`.
*   `amount` (DOUBLE): Dollar value (positive = inflow, negative = outflow).
*   `direction` (VARCHAR): Inflow vs Outflow.
*   `transaction_type` (VARCHAR): ACH, Wire, Check, Debit, etc.
*   `counterparty_type` (VARCHAR): Vendor, Customer, Tax, Payroll, etc.
*   `payment_channel` (VARCHAR): Online, POS, Branch, etc.
*   `is_recurring` (INTEGER): Flag for recurring items.
*   `source_system` (VARCHAR): Core banking channel source.
*   `transaction_memo` (VARCHAR): Narrative text.

### Table: `invoices`
*Grain: Invoice (90,000 rows)*
*   `invoice_id` (VARCHAR): Unique invoice ID.
*   `business_id` (VARCHAR): Business that issued the invoice.
*   `invoice_date` (DATE): Issue date.
*   `invoice_month` (VARCHAR): Month format `YYYY-MM`.
*   `invoice_amount` (DOUBLE): Total invoiced value.
*   `due_date` (DATE): Payment deadline.
*   `paid_date` (DATE): Actual payment date.
*   `days_to_pay` (INTEGER): Duration between issue and payment.
*   `payment_status` (VARCHAR): Paid on time, late, unpaid, etc.
*   `is_late` (INTEGER): Flag for late payment.
*   `customer_type` (VARCHAR): Enterprise client, government, consumer, etc.
*   `customer_concentration_rank` (INTEGER): Importance rank.
*   `invoice_channel` (VARCHAR): Portal, EDI, paper, etc.

### Table: `loans`
*Grain: Loan (2,800 rows)*
*   `loan_id` (VARCHAR): Unique loan ID.
*   `business_id` (VARCHAR): Business borrower ID.
*   `product_type` (VARCHAR): Term Loan, Line of Credit, Invoice Financing.
*   `loan_amount` (DOUBLE): Principal amount.
*   `start_date` (DATE): Origination date.
*   `interest_rate` (DOUBLE): Loan APR.
*   `loan_term_months` (INTEGER): Maturity tenure.
*   `maturity_date` (DATE): Scheduled maturity.
*   `collateral_type` (VARCHAR): UCC lien, real estate, equipment, unsecured.
*   `secured_flag` (INTEGER): Flag indicating collateral presence.
*   `origination_channel` (VARCHAR): Branch, online, broker.
*   `underwriting_score_band` (VARCHAR): Internal underwriting score band.
*   `initial_risk_grade` (VARCHAR): Grade assigned at origination.

### Table: `repayments`
*Grain: Repayment event (46,790 rows)*
*   `repayment_id` (VARCHAR): Unique repayment ID.
*   `loan_id` (VARCHAR): Linked loan ID.
*   `business_id` (VARCHAR): Borrower ID.
*   `payment_month` (VARCHAR): Scheduled month `YYYY-MM`.
*   `scheduled_amount` (DOUBLE): Monthly repayment due.
*   `actual_payment` (DOUBLE): Amount paid.
*   `days_past_due` (INTEGER): Days past due.
*   `payment_status` (VARCHAR): status (on_time, late, default).
*   `principal_remaining` (DOUBLE): Loan balance outstanding.
*   `auto_debit_success_flag` (INTEGER): Flag for auto-debit success.
*   `payment_channel` (VARCHAR): ACH, check, auto-debit.

### Table: `payroll`
*Grain: Payroll month (36,000 rows)*
*   `payroll_id` (VARCHAR): Unique payroll record.
*   `business_id` (VARCHAR): Business ID.
*   `payroll_month` (VARCHAR): Month format `YYYY-MM`.
*   `employee_count` (INTEGER): Total payroll employees.
*   `full_time_count` (INTEGER): Full-time employee count.
*   `part_time_count` (INTEGER): Part-time employee count.
*   `payroll_amount` (DOUBLE): Total monthly payroll cost.
*   `avg_wage_estimate` (DOUBLE): Average wage estimate.
*   `overtime_hours_proxy` (DOUBLE): Proxy of overtime hours.
*   `payroll_processor` (VARCHAR): ADP, Gusto, Paychex, etc.

### Table: `business_monthly_snapshots`
*Grain: Business-Month (36,000 rows)*
*Pre-calculated aggregation of key indicators over 24 months.*
*   `business_id`, `month`, `month_start_date`
*   `opening_cash_balance_proxy`, `ending_cash_balance_proxy`, `avg_daily_balance_proxy`
*   `overdraft_days_proxy`
*   `transaction_count`, `cash_inflow_observed`, `cash_outflow_observed`, `net_cash_flow_observed`
*   `invoice_count`, `invoice_amount_total`, `avg_days_to_pay`, `late_invoice_rate`
*   `payroll_amount`, `employee_count`
*   `scheduled_debt_service`, `actual_debt_service`, `max_dpd`
*   `available_credit_drawn_ratio`

### Table: `business_monthly_outcomes`
*Grain: Business-Month (36,000 rows)*
*Optional forward-looking labels (useful for target evaluation).*
*   `business_id`, `month`
*   `future_60d_dpd30_flag` (INTEGER): Business goes DPD > 30 within next 60d.
*   `future_60d_negative_cashflow_flag` (INTEGER): Negative cash flow within next 60d.
*   `future_60d_collection_delay_spike_flag` (INTEGER): Spike in collection delays.
*   `future_60d_cash_stress_observed` (INTEGER): General 60d cash stress event (combines flags).

### Table: `credit_reviews`
*Grain: Review event (9,898 rows)*
*Tracks historical credit interventions.*
*   `review_id`, `business_id`, `review_month`
*   `review_type` (VARCHAR): automated, manual.
*   `review_action` (VARCHAR): watchlist_add, limit_decrease, manual_review, none.
*   `internal_watchlist_flag_after_review` (INTEGER): Watchlist status (0/1).
*   `review_reason` (VARCHAR): cash_flow_change, collection_delay, etc.
*   `notes_available_flag` (INTEGER): Indicator for qualitative notes.

### Table: `industry_benchmark`
*Grain: Industry (12 rows)*
*Reference values for comparing businesses against their peers.*
*   `industry_id`, `industry`
*   `benchmark_margin`, `benchmark_cash_flow_volatility`
*   `benchmark_collection_days`, `benchmark_repayment_burden_pct`
*   `payroll_intensity`, `seasonality_peak_month`, `typical_transaction_intensity`, `economic_sensitivity`

### Table: `region_dim`
*Grain: Region (5 rows)*
*Geographic indicators.*
*   `region_id`, `region`, `state`, `cost_index`, `baseline_unemployment_proxy`

### Table: `region_macro_index`
*Grain: Region-Month (144 rows)*
*Macroeconomic indexes over time.*
*   `month`, `region_id`, `region`
*   `interest_rate_proxy`, `local_demand_index`, `small_business_confidence_index`, `unemployment_proxy`

### Table: `relationship_managers`
*Grain: RM (60 rows)*
*Portfolio owners.*
*   `relationship_manager_id`, `region_id`, `portfolio_focus`, `years_experience`, `portfolio_size_band`

### View: `vw_table_row_counts`
*Dynamic count helper.*
*   `table_name` (VARCHAR), `row_count` (BIGINT)

---

## 6. Analytical Tables, Models, Pipelines, and Dashboards Status

*   **Existing pipelines:** None.
*   **Existing analytical tables:** The only structured tables are raw transactions and snapshots. There is no customized wide feature table or active output table (e.g. `customer_risk_alerts`).
*   **Existing models:** None.
*   **Existing dashboards:** None.
*   **Existing reports:** None.
*   **Existing notebooks:** One placeholder, [01_starter_analysis.ipynb](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sme_cashflow_stress_project/notebooks/01_starter_analysis.ipynb).

---

## 7. Execution Commands Currently Required

Since the project is not automated or packaged, there are only test/validation commands available:
1.  **Testing Database Connection:**
    ```bash
    python src/starter_framework.py
    ```
2.  **Launching the Jupyter Notebook Environment:**
    ```bash
    jupyter notebook notebooks/01_starter_analysis.ipynb
    ```

---

## 8. Risks, Inconsistencies, and Obstacles

> [!IMPORTANT]
> The following list outlines structural issues, path inconsistencies, and data leakage risks that must be resolved prior to implementing CashFlow Guardian.

1.  **Colab vs. Local Paths:**
    *   In the `README.md` the connection is described using `/content/sme_cashflow_stress_project/...` which is Colab-specific.
    *   `notebooks/01_starter_analysis.ipynb` connects to `../data/sme_cashflow_stress.duckdb`. If run from any other folder, this fails.
    *   `src/starter_framework.py` resolves pathing using `Path(__file__).resolve()`, which is correct. We must enforce this path resolution across all components.
2.  **Data Leakage Risk (Lookahead Bias):**
    *   The `business_monthly_outcomes` contains future indicators (e.g., `future_60d_cash_stress_observed`). In `03_modeling_dataset_template.sql`, these are joined by month directly.
    *   When constructing training datasets, we must ensure features are computed using only data available *prior* to the prediction point (e.g., for prediction at month $T$, features can only use transactional data up to month $T$, while the label looks forward to $T+1$ and $T+2$). Any rolling average that spans into $T+1$ would leak future outcomes.
3.  **Missing Dependencies:**
    *   There is no file listing packages like `requirements.txt` or `pyproject.toml`. Standard libraries are used, but `duckdb`, `pandas`, `numpy`, `scikit-learn`, `xgboost`, `matplotlib`, and `streamlit` are missing from the configuration.
4.  **Lack of Database Constraints:**
    *   DuckDB columns are all listed with `key = None`. No constraints are enforced. Relationships must be validated in pipelines to avoid duplicates or orphan records (e.g., orphans in `loans` without valid `business_id`).
5.  **Incomplete/Null Outcomes at Boundaries:**
    *   The outcomes table contains `<NA>` values for the last two months of the dataset (`2025-11` and `2025-12`) because the 60-day horizon falls outside the dataset boundary. The modeling pipeline must filter these out when preparing training labels.

---

## 9. Recommended Migration Plan to CashFlow Guardian

To migrate this analytics project to **CashFlow Guardian**, we will transition it from a static dataset to an end-to-end predictive risk monitoring application.

### Proposed Architecture Diagram

```mermaid
graph TD
    %% Data layer
    subgraph Data Layer
        DB[(DuckDB Database)]
        CSV[Raw CSV Files]
    end
    
    %% Pipeline layer
    subgraph Core Pipeline (Python & SQL)
        Ingest[Ingestion/Validation Pipeline]
        Transform[Transformation/Features Engine]
        FeatureStore[(Wide Feature Table)]
    end
    
    %% ML Layer
    subgraph Machine Learning Stack
        Prep[Train/Test Split & Scaler]
        Train[Model Training: XGBoost/LightGBM]
        Predict[Inference Engine]
        Models[(Serialized Models)]
    end

    %% Agent Layer
    subgraph Agentic Reasoning
        Agent[Risk Explanation & Strategy Agent]
        LLM[LLM Service]
    end
    
    %% Dashboard Layer
    subgraph Presentation (UI)
        Dashboard[Streamlit Web App]
    end

    %% Flow connections
    CSV --> Ingest
    Ingest --> DB
    DB --> Transform
    Transform --> FeatureStore
    FeatureStore --> Prep
    Prep --> Train
    Train --> Models
    Models --> Predict
    FeatureStore --> Predict
    Predict --> DB
    
    %% Agent interactions
    DB --> Agent
    Agent --> LLM
    
    %% Dashboard consumption
    DB --> Dashboard
    Agent --> Dashboard
```

### Migration Phases

#### Phase 1: Setup & Data Pipeline Foundation (Week 1 Equivalent)
*   **Dependency Management:** Create a structured `pyproject.toml` or `requirements.txt` defining all environments (duckdb, streamlit, xgboost, scikit-learn, etc.).
*   **Modular Pipeline:** Develop a Python transformation module `src/pipelines/features.py` that executes parameterized SQL (migrated from `02_cashflow_metric_baseline.sql`) and writes a persistent `analytical_features_wide` table to the database.
*   **Data Validation:** Build tests to verify data integrity, check for duplicates, and ensure no data leakage.

#### Phase 2: Predictive Modeling Pipeline (Week 2 Equivalent)
*   **Feature Engineering:** Systematically generate lagging indicators, ratios (repayment burden, payroll burden), and volatility metrics over 3-month and 6-month windows.
*   **Time-Series CV:** Implement a rolling-window cross-validation split in `src/modeling/train.py` to prevent data leakage and evaluate the model on historical test sets.
*   **Model Training:** Train an XGBoost or LightGBM classifier to predict probability of 60-day cash stress. Save model metrics, feature importances, and the serialized model binary.
*   **Inference Engine:** Build a prediction script `src/modeling/predict.py` that computes risk scores for the latest active month for all 1,500 businesses and saves predictions to a `business_risk_scores` table.

#### Phase 3: Agentic Reasoning & Recommendation System (Week 3 Equivalent)
*   **Risk Explanation:** Build a reasoning engine `src/agent/risk_agent.py` that queries a customer's monthly snapshots and benchmarks.
*   **Strategy Recommendations:** Define a decision matrix matching risk scores (Red/Amber/Green) and underlying causes to bank policies (e.g. limit decrease, credit review, watchlist addition). The agent generates a qualitative summary detailing why the business is under stress and the exact playbook steps to follow.

#### Phase 4: Production Streamlit Dashboard (Week 4 Equivalent)
*   **Portfolio Overview Tab:** High-level key indicators (stressed count, total exposed exposure, breakdown by industry and region).
*   **Watchlist Grid:** Sortable table of all businesses, filtered by risk tier and relationship manager, showing current balances, risk score, and primary risk driver.
*   **Customer Detail View:** A dedicated screen for relationship managers:
    *   Interactive plots of cash inflow, outflow, and balances over time.
    *   Comparisons of the business's collection days and margins against its industry benchmarks.
    *   Agent-generated natural language risk summary and action playbooks.
    *   An interactive form allowing relationship managers to log notes and record credit review actions.

---

## 10. Next Steps

Please review this inventory and audit report. Once approved, we will:
1.  Establish the python workspace dependencies.
2.  Begin executing the transformation pipeline to build the analytical wide features.
3.  Design and implement the modeling stack.

*Status: Awaiting Approval.*
