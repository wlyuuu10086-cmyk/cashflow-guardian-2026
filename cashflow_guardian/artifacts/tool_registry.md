# CashFlow Guardian - Tool Registry Report

This report presents a complete catalog of registered, schema-enforced tools available for agent invocation. All metadata is verified against `specs/tool_contracts.yaml` at load time.

## Registered Tools Catalog

| Canonical Name | Purpose | Permission | Approval Required | Input Schema | Output Schema | Source Tables |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **`check_database_health`** | Verifies DuckDB connection status and ensures source tables are accessible and read-only. | `read-only` | No | `{}` | `{status: string, read_only_verified: boolean, database_size_bytes: integer}` | `vw_table_row_counts` |
| **`check_business_data_quality`** | Evaluates the data presence, null counts, and history duration for a given business before scoring. | `read-only` | No | `{business_id: string, month: string}` | `DataQualityResult` | `business_customers`, `business_monthly_snapshots` |
| **`get_portfolio_snapshot`** | Retrieves risk tiers, risk scores, and principal evidence for all SMEs for a target as-of month. | `read-only` | No | `{month: string}` | `PortfolioSnapshotResult` | `business_customers`, `business_monthly_snapshots` |
| **`get_business_history`** | Fetches historical cash flow snapshot data for a specific business up to the selected as-of month. | `read-only` | No | `{business_id: string, month: string}` | `BusinessHistoryResult` | `business_monthly_snapshots` |
| **`build_point_in_time_features`** | Calculates rolling averages, change ratios, and volatility for a business as of a point-in-time. | `read-only` | No | `{business_id: string, month: string}` | `FeatureVectorResult` | `business_monthly_snapshots`, `bank_transactions`, `repayments`, `invoices`, `payroll` |
| **`score_cashflow_risk`** | Invokes the risk model pipeline to score a business's 60-day cash stress probability. | `read-only` | No | `{business_id: string, month: string}` | `{business_id: string, month: string, risk_score: number, risk_tier: string, model_version: string, feature_contributions: array}` | None |
| **`compare_with_peers`** | Benchmarks a business's cash flow features against its industry segment benchmarks. | `read-only` | No | `{business_id: string, month: string}` | `PeerBenchmarkResult` | `industry_benchmark`, `business_customers`, `business_monthly_snapshots` |
| **`simulate_cashflow_scenario`** | Runs a deterministic calculation of projected cash balance and stress based on shock parameters. | `read-only` | No | `{business_id: string, month: string, cash_inflow_multiplier: number, cash_outflow_multiplier: number, collection_delay_days: integer}` | `{business_id: string, month: string, baseline_cash_balance: number, simulated_cash_balance: number, projected_overdraft_risk: boolean, risk_tier_change: string}` | `business_monthly_snapshots` |
| **`draft_intervention_plan`** | Maps specific cash flow risk evidence (e.g. late invoices vs loan burden) to policy-compliant action recommendations. | `read-only` | No | `{risk_tier: string, primary_risk_driver: string}` | `{risk_tier: string, recommended_playbook: string, allowed_actions: array}` | None |

## Prohibited Behaviors and Security Policy
The tool registry strictly blocks the registration or execution of tools that perform any of the following:
* Direct SQL Execution (`execute_sql`, `run_sql`, etc.)
* Writing or modifying the DuckDB database tables
* Contacting external systems or sending automated emails
* Initiating ACH, wires, or loans
* Altering customer records or credit limits
