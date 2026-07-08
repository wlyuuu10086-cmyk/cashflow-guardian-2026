# Product Specification: CashFlow Guardian

## 1. Executive Summary
CashFlow Guardian is an Agentic Early-Warning and Decision-Support System for Small and Medium Enterprise (SME) Cash-Flow Stress. It empowers financial institutions to move from reactive risk management (acting after default has occurred) to proactive risk management by combining predictive machine learning models, deterministic scenario engines, and an Agentic LLM router. The system processes bank transactions, loan repayment histories, invoices, and macroeconomic indicators, generating early warnings, explaining complex risks, and drafting intervention playbooks.

* **Project Name:** CashFlow Guardian
* **Subtitle:** An Agentic Early-Warning and Decision-Support System for SME Cash-Flow Stress
* **Primary Track:** Agents for Business
* **Primary Users:** SME Relationship Managers (RMs), Credit Risk Analysts, Portfolio Monitoring Teams

---

## 2. Target Users & Problem Space

### 2.1 Target Users
* **SME Relationship Managers (RMs):** Manage portfolios of SME clients. They need immediate, clear, non-technical explanations of why a client is flagged for cash-flow stress, benchmarks comparing the client to industry peers, and actionable intervention plans to discuss with the client.
* **Credit-Risk Analysts:** Conduct in-depth credit reviews. They require precise, point-in-time traceable transaction indicators, cash flow projections, and simulated impacts of downside scenarios to make credit grading decisions.
* **Portfolio Monitoring Teams:** Monitor overall portfolio health. They need as-of-month portfolio scans to see aggregate risk distribution, identify clusters of stress (e.g., specific industries or regions), and track watchlist status.

### 2.2 User Problems
* **Lagging Indicators:** Traditional credit scoring relies on quarterly financial statements or actual payment defaults (Days Past Due > 30/90), which occur long after cash-flow stress has set in.
* **Alert Fatigue:** Existing early-warning systems generate generic alerts (e.g., "Cash balance dropped below threshold") without context, forcing analysts to manually compile data across multiple tools.
* **Complexity of Cash Flow Dynamics:** Cash-flow stress is multi-causal. A decline in cash could stem from late customer invoice payments, a payroll spike, or rising debt burden. Identifying the root cause requires complex temporal aggregates.
* **Lack of Actionable Next Steps:** Systems flag risks but rarely suggest safe, policy-compliant draft interventions (e.g., line-of-credit restructuring, invoice factoring options).

### 2.3 Why an Agent is Necessary Instead of a Static Dashboard
While a static dashboard can display charts of historical cash balances, it fails to solve the user's primary decision bottlenecks:
1. **Context Synthesis:** An agent can trace a risk score to its core drivers (e.g., "The risk score rose to 84% primarily due to a 25-day increase in customer collection times combined with a high debt-service burden") and write a human-readable synthesis.
2. **Intent-Driven Exploration:** Users can query in natural language (e.g., "Explain why Acme Corp is flagged as Red, and simulate a 20% drop in cash inflows") rather than toggling multiple filters and tabs.
3. **Dynamic Playbook Formulation:** The agent acts as an Orchestrator that queries policy files, checks current metrics, and drafts a contextual intervention plan tailored to the specific stress driver, which RMs can directly use as a template.
4. **Human-in-the-Loop Integration:** The agent acts as a guard, drafting watchlist proposals that require explicit RM approval, ensuring compliance and recording audit trails without manual database logging.

---

## 3. One-Day MVP Scope & Workflows

The MVP is scoped to deliver three core workflows and one Human-in-the-Loop action:

### Workflow 1: Portfolio Scan
* **Description:** Allows the user to select an as-of month to inspect the risk status of all businesses.
* **Inputs:** `as_of_month` (YYYY-MM).
* **System Execution:**
  * Validates the selected month exists in the database.
  * Queries point-in-time risk scores and details.
  * Groups businesses by Risk Tier (Red/Amber/Green RAG classification).
* **Outputs:** A structured table containing business name, business ID, risk tier, risk score, principal evidence (e.g., high volatility, rising late invoices), and data-quality status (e.g., complete vs. warnings).

### Workflow 2: Business Investigation
* **Description:** Conducts a deep-dive analysis on a specific business at a selected as-of month.
* **Inputs:** `business_id`, `as_of_month` (YYYY-MM).
* **System Execution:**
  * Validates the business ID and month.
  * Retrieves historical metrics (cash balances, transaction counts, payroll, debt payments).
  * Evaluates or retrieves the predictive risk score for that month.
  * Selects the peer group and fetches benchmark comparison values (benchmark margins, typical collection days).
  * The Agent synthesizes this evidence into a cohesive narrative explaining the risk drivers.
* **Outputs:** 
  * A detailed financial health report including historical charts (observed data).
  * Comparison tables with industry peers (margins, collection delays, volatility).
  * Traceable natural-language explanation of risk indicators. Every number in the narrative must be traceable to deterministic tool outputs.

### Workflow 3: Scenario Simulation
* **Description:** Runs deterministic what-if simulations on a business's future cash flows based on user assumptions.
* **Inputs:** `business_id`, `as_of_month` (YYYY-MM), cash inflow multiplier (e.g., -10%), cash outflow multiplier (e.g., +5%), collection delay change (e.g., +15 days).
* **System Execution:**
  * Retrieves the baseline point-in-time metrics.
  * Applies the shock multipliers via deterministic Python math (no LLM calculations).
  * Re-evaluates projected liquidity metrics and risk thresholds.
  * Distinguishes observed data from simulated projections in the UI and reports.
* **Outputs:** A comparison showing:
  * Baseline cash balances and RAG status.
  * Simulated cash balances, projected overdraft risk, and estimated risk tier.
  * Agent explanation of the simulated impacts on the business's survival runway.

### Human-in-the-Loop (HITL) Action
* **Action:** Propose adding a business to the demonstration watchlist.
* **Constraints:**
  1. The action must be drafted by the Agent but **cannot execute** until a human explicitly clicks approval in the UI.
  2. The original source DuckDB database remains strictly read-only.
  3. Approved watchlist actions are written only to a separate local demo action store: `data/demo_actions.json`.

---

## 4. Explicit Non-Goals
To manage risk and bound the Capstone scope, the following are strictly out of scope for both the MVP and future iterations:
* **No Real Lending Decisions:** The system does not automatically approve or deny loans.
* **No Credit-Limit Changes:** The system cannot modify or initiate real credit limit adjustments in banking core systems.
* **No Real Customer Contact:** The system will not send automated emails, messages, or notices to the SME business owner.
* **No Real Payment Execution:** The system cannot initiate ACH, wires, or transfer requests.
* **No Modification of Source Financial Data:** Under no circumstance will the source transactions, loan tables, or outcome tables in the DuckDB database be modified or overwritten.
* **No Replacement of Human Judgment:** The system acts strictly as decision-support. All final credit grades and intervention actions must be made by qualified human professionals.

---

## 5. Requirements

### 5.1 Functional Requirements
* **FR-1 (Point-in-Time Enforcement):** All queries and features for month $T$ must ignore transactions or snapshots occurring in month $T+1$ or later.
* **FR-2 (No LLM Math):** All financial calculations, multipliers, and averages must be calculated in Python or SQL, and passed as structured evidence.
* **FR-3 (Traceability):** Every metric returned to the user must carry provenance metadata (source tables, query timestamp, row counts, future data flags).
* **FR-4 (HITL Action Logging):** Watchlist proposals must capture: `business_id`, `proposer_role`, `proposal_timestamp`, `status` (pending/approved/rejected), `approver_id`, and `audit_timestamp`.

### 5.2 Non-Functional Requirements
* **NFR-1 (Security & Sandboxing):** Transaction memo fields must be treated as untrusted user inputs. The Agent must be protected against prompt injections within these fields.
* **NFR-2 (SQL Parameterization):** No arbitrary SQL strings generated by LLMs may be executed. All database access must go through pre-defined, parameterized templates.
* **NFR-3 (Performance):** Portfolio scan queries and risk scores must execute in under 2 seconds to support interactive dashboard interactions.

---

## 6. One-Day MVP Implementation Priorities

We classify the system requirements into P0 (essential for today's Capstone demo), P1 (secondary), and P2 (deferred):

| Requirement | Description | Priority |
| :--- | :--- | :---: |
| **Data Engine** | Reads DuckDB, computes point-in-time features, handles data QA | **P0** |
| **Predictive Model** | Enforces one defensible ML model (Logistic Regression baseline, 1 Tree candidate) | **P0** |
| **Three Workflows** | Portfolio scan, business investigation, and what-if scenario calculator | **P0** |
| **Early Warning Agent** | routes query intents, synthesizes data, explains triggers | **P0** |
| **Watchlist HITL** | Agent proposes, UI approves, writes to `data/demo_actions.json` | **P0** |
| **Streamlit Interface** | Interactive UI containing the three workflows and HITL buttons | **P0** |
| **Security Controls** | Parameterized tools, prompt injection protection, read-only verification | **P0** |
| **Deterministic Tests** | Unit tests checking data leakage, read-only checks, and metrics | **P0** |
| **Agent Evals** | Set of at least 10 evaluation cases to check routing and synthesis | **P0** |
| **Automated Alerts** | Real-time SMS/email alerts to RMs when a new alert is generated | **P2** |
| **Multi-Agent Negotiation** | RM agent and Risk officer agent negotiating limits | **P2** |
| **Core Bank Integration** | Live writes back to banking core transactional systems | **P2** |
| **Auto-retraining Pipeline** | Automated weekly model training and shadow deployment | **P2** |

---

## 7. Limitations & Refusal-to-Score Conditions
The system must refuse to score a business and raise an informative error/warning under the following conditions:
1. **Insufficient Historical Data:** The business has less than 3 months of active transactions or snapshots since its onboarding date.
2. **Missing Vital Snapshot Data:** If core financial fields like `ending_cash_balance` or `cash_inflow` are completely missing for the active month.
3. **Out-of-Bounds Month:** If the requested `as_of_month` is outside the synthetic dataset date range (`2024-01` to `2025-12`).
4. **Data Quality Status is Blocked:** If raw validation checks flag massive transaction gaps indicating database corruption.
