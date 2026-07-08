# SME Cash Flow Stress Early Warning System - Student Package

This package contains a synthetic DuckDB dataset and starter files for an 8-week internship project.

## Project Goal
Build an SME cash flow stress early warning system that helps a financial institution identify businesses with potential cash flow pressure earlier and design differentiated intervention strategies.

## How to Use DuckDB in Python / Colab
```python
!pip install duckdb
import duckdb, pandas as pd
DB_PATH = "/content/sme_cashflow_stress_project/data/sme_cashflow_stress.duckdb"
con = duckdb.connect(DB_PATH)
con.sql("SHOW TABLES").df()
con.sql("SELECT * FROM vw_table_row_counts ORDER BY row_count DESC").df()
```

For local use from the project folder:
```python
con = duckdb.connect("data/sme_cashflow_stress.duckdb")
```

## Folder Structure
```text
sme_cashflow_stress_project/
  data/sme_cashflow_stress.duckdb
  data/csv/*.csv
  docs/data_dictionary.csv
  docs/project_brief.md
  docs/week_plan.md
  sql/*.sql
  src/starter_framework.py
  notebooks/01_starter_analysis.ipynb
```

## Key Tables
| Table | Grain | Purpose |
|---|---|---|
| business_customers | business | Business profile and segmentation fields |
| industry_benchmark | industry | Industry benchmark margin, volatility, collection days |
| region_macro_index | region-month | Local macro demand and confidence indicators |
| loans | loan | Loan amount, product, rate, term, collateral |
| repayments | loan-month | Scheduled/actual payment, DPD, repayment status |
| bank_transactions | transaction | Operating inflows and outflows from bank accounts |
| invoices | invoice | Invoice issue, due, paid dates and collection delay |
| payroll | business-month | Payroll expense and employee counts |
| business_monthly_snapshots | business-month | Monthly observed aggregates for QA/dashboarding |
| business_monthly_outcomes | business-month | Optional forward-looking outcomes for label construction |
| credit_reviews | review event | Watchlist and credit review actions |

## Dataset Size
Approximately 742,018 rows across 13 tables. It is designed to run on a normal laptop with DuckDB.

## Student Notes
Use raw event tables to build your own metrics. The outcome table is optional for modeling. Avoid leakage by using only information available before the prediction window.
