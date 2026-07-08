# Implementation Plan - CashFlow Guardian Specifications & Configurations

This implementation plan outlines the strategy to establish the authoritative project specifications and configuration files for the **CashFlow Guardian** one-day MVP. During this phase, no application implementation files or logic will be written, and no database schemas will be modified. We will focus purely on specification, configuration, behavior definition, and compliance policies.

## User Review Required

> [!IMPORTANT]
> **Key Architectural Decisions & Guardrails:**
> 
> 1. **Read-Only Source Database:** The existing DuckDB database (`sme_cashflow_stress_project/data/sme_cashflow_stress.duckdb`) is strictly read-only.
> 2. **Demo Action Store:** All watchlist proposals approved by the human-in-the-loop (HITL) action will be written to a separate local demo store (a local SQLite database or JSON file `data/demo_actions.json`) to keep the source tables pristine.
> 3. **Strict Pathing:** We resolve all paths relative to the `cashflow_guardian` directory using dynamic pathing (not hardcoded paths) to avoid Colab vs. Local path mismatches.
> 4. **No Arbitrary SQL for Agent:** The Early Warning Agent will not have access to any arbitrary SQL execution tool. All queries are pre-defined, parameterized, and restricted to safe APIs.
> 5. **Lookahead Bias Prevention:** For inference at month $T$, no data (including transactions, outcomes, or reviews) after month $T$ will be visible to features or models.

> [!WARNING]
> **Contradictions with Starter SQL Templates:**
> - In `03_modeling_dataset_template.sql`, the future outcome table is joined directly. In the production code, we must enforce that the outcome table (`business_monthly_outcomes`) is **never** used during normal inference or returned to the Agent.
> - The target label must be audited. We will require filtering out boundary rows (`2025-11` and `2025-12`) during model training/evaluation because the 60-day window is truncated.

## Proposed Changes

We will create and fully update exactly 20 specification and configuration files under the `d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian` folder:

### Component: Specifications (`specs/`)

#### [NEW] [product_spec.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/product_spec.md)
Executive summary, target users, core MVP workflows, explicit non-goals (no real lending decisions, no real transaction execution), success criteria, and priority classifications (P0/P1/P2).

#### [NEW] [architecture.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/architecture.md)
Mermaid diagrams of system architecture and agent workflows, module paths (under `src/cashflow_guardian`), deterministic vs. LLM responsibilities, point-in-time flow, and HITL sequence.

#### [NEW] [behaviors.feature](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/behaviors.feature)
Gherkin behavior tests (14 distinct testable scenarios) covering successful scans, low/high-risk investigations, validation errors, prompt injection, and unauthorized write attempts.

#### [NEW] [data_contracts.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/data_contracts.yaml)
Structured YAML schemas for business identifiers, history, snapshots, benchmarking, feature vectors, and provenance metadata.

#### [NEW] [tool_contracts.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/tool_contracts.yaml)
Definitions for 11 specific, parameterized tools (no arbitrary SQL execution). Inputs, outputs, allowed source tables, and permission levels.

#### [NEW] [model_spec.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/model_spec.md)
Target label definitions, chronological time-series splitting, XGBoost/LightGBM specifications, metrics (recall, PR-AUC, calibration), and refusal-to-score conditions.

#### [NEW] [evaluation_spec.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/evaluation_spec.md)
Validation strategy for deterministic software, ML models, agent actions (eval dataset of 10 cases), security controls, and HITL.

#### [NEW] [security_requirements.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/security_requirements.md)
Threat boundaries, prompt-injection mitigations, transaction memo parsing restrictions, credential protection, and PII masking.

#### [NEW] [deployment_spec.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/deployment_spec.md)
Local deployment setups (Python, DuckDB, ADK playbooks, Streamlit) and configuration placeholders.

#### [NEW] [demo_scenarios.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/specs/demo_scenarios.md)
Six exact, step-by-step user-testing flows to demonstrate system robustness during the Capstone review.

### Component: Root Documentation

#### [NEW] [AGENTS.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/AGENTS.md)
Rules for agent collaboration: read specs first, never alter raw data, use deterministic code for math, enforce no future leakage.

#### [NEW] [GEMINI.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/GEMINI.md)
Antigravity specific workflow rules, plan validation, diff usage, test automation, and code cleanliness.

### Component: System Configuration (`config/`)

#### [NEW] [app.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/app.yaml)
High-level application properties, name, description, logging levels, and API targets.

#### [NEW] [database.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/database.yaml)
Connection configs, relative paths, read-only setting, and demo action store write paths.

#### [NEW] [model.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/model.yaml)
Model parameters, feature lists, versioning details, and scoring configurations.

#### [NEW] [thresholds.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/thresholds.yaml)
Risk score thresholds (Red/Amber/Green RAG limits), repayment burden, and payroll intensity warning levels.

#### [NEW] [environments/local.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/environments/local.yaml)
Local development execution environment settings.

#### [NEW] [environments/test.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/environments/test.yaml)
Automated test pipeline properties.

#### [NEW] [environments/demo.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/config/environments/demo.yaml)
Interactive capstone presentation settings.

#### [NEW] [policies.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/policies.yaml)
Formal policy enforcement criteria: read-only constraints, HITL action rules, security allowlists, and logging masks.

---

## Verification Plan

### Automated Check
- **YAML Validation:** Parse `data_contracts.yaml`, `tool_contracts.yaml`, and all configurations using python standard parser to ensure syntactic correctness.
- **Path Verification:** Check that directory paths used in configs correspond to correct local paths.

### Manual Verification
- **Cross-File Consistency:** Check that all tool names match between `tool_contracts.yaml` and `architecture.md`.
- **Feature Coverage:** Confirm that all 14 scenarios defined in `behaviors.feature` are addressed in product specs and test scripts.
- **Export Review:** Generate `artifacts/specification_review.md` compiling validation checks.
