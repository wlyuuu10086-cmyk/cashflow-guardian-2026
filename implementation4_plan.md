# CashFlow Guardian - Step 5 Implementation Plan: Business Capability Layer & Structured Tools

This document outlines the detailed design and implementation strategy for the **Benchmark Engine**, **Scenario Engine**, **Intervention Engine**, and **Structured Agent Tools** in the CashFlow Guardian system.

---

## Goal Description
Implement the deterministic business-capability layer that exposes portfolio analytics, peer benchmarking, what-if cash-flow scenario simulations, and draft intervention playbooks to the future LLM Early Warning Agent. 

All financial calculations and rules are implemented deterministically in Python/SQL. The future LLM will only consume the outputs of these tools and is strictly prohibited from executing any math or database writes.

---

## User Review Required

> [!IMPORTANT]
> **Performance Optimization via Model Caching:** To prevent loading serialized joblib models on every prediction (which would crash performance during portfolio scanning), we will implement a lightweight `lru_cache` in [model_loader.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/model_loader.py).

> [!WARNING]
> **Boundary Limits & Verification:** Scenario simulations will strictly validate input ranges (e.g., inflow changes between -100% and +200%). Any out-of-bounds parameters will raise typed `ValueError` exceptions immediately, rather than silently clamping.

---

## Open Questions
There are no open questions. The specifications provided in the behavioral feature file, product spec, and data contracts define the required boundaries.

---

## Proposed Changes

### Component 1: Risk Engine (Caching Optimization)

#### [MODIFY] [model_loader.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/risk_engine/model_loader.py)
* Wrap model-loading and configuration functions with `functools.lru_cache(maxsize=1)` to prevent repeated disk read and deserialization operations in tight loops (e.g., during portfolio scans).

---

### Component 2: Benchmark Engine

Provides point-in-time safe, deterministic benchmarking of business performance against industry peers.

#### [NEW] [schemas.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/benchmark_engine/schemas.py)
* Define Pydantic models for peer group comparisons:
  * `PeerGroupDefinition`: contains `method` (selection strategy), `industry`, `revenue_band`, and `peer_count`.
  * `BenchmarkMetricComparison`: details business value, peer median/benchmark, absolute gap, percentage gap, percentile rank, comparison direction (`better`, `similar`, `worse`, `unavailable`), interpretation code, and source provenance.
  * `BenchmarkProvenance`: source tables, month, timestamp, and leakage checks.
  * `BusinessBenchmarkResult`: maps business ID and month to compared metrics.

#### [NEW] [peer_groups.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/benchmark_engine/peer_groups.py)
* Implement peer group identification logic with minimum size rule (e.g., $\ge 5$ peers):
  * **Preferred Group:** same industry + same revenue band in target month.
  * **Fallback:** same industry in target month.
  * **Final Fallback:** `industry_benchmark` table reference values.
* Record the method used.

#### [NEW] [comparison.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/benchmark_engine/comparison.py)
* Implement public function `compare_business_with_peers(business_id: str, as_of_month: str)`.
* Query peer values for 8 core metrics:
  1. Cash-flow volatility (6-month net cash flow sample standard deviation)
  2. Average collection days (`avg_days_to_pay`)
  3. Late invoice rate (`late_invoice_rate`)
  4. Repayment burden ratio (`scheduled_debt_service / cash_inflow`)
  5. Payroll burden ratio (`payroll_amount / cash_inflow`)
  6. Credit utilization (`available_credit_drawn_ratio`)
  7. Overdraft days (`overdraft_days_proxy`)
  8. Three-month net cash-flow trend (Net cash flow at month $T$ minus month $T-2$)
* Determine direction (`better`, `similar`, `worse`) based on configured tolerances (e.g., collection days $\pm 5$ days, ratio $\pm 5\%$).

#### [MODIFY] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/benchmark_engine/__init__.py)
* Expose `compare_business_with_peers` at the package level.

---

### Component 3: Scenario Engine

Performs deterministic cash-flow scenario simulations using user-defined shock multipliers.

#### [NEW] [schemas.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/scenario_engine/schemas.py)
* Define Pydantic models:
  * `ScenarioBaseline` / `ScenarioSimulated`: Cash inflow, outflow, net cash flow, payroll, debt service, collection days, repayment/payroll burden ratios, liquidity gap, risk score, and risk tier.
  * `ScenarioResult`: business details, assumptions, baseline and simulated results, score change, tier change, scoring mode, model version, and provenance/warnings.

#### [NEW] [assumptions.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/scenario_engine/assumptions.py)
* Implement safe input validation ranges:
  * Inflow change: -100% to +200%
  * Outflow change: -100% to +200%
  * Collection delay: -60 to +180 days
  * Payroll change: -100% to +200%
  * Debt-service change: -100% to +200%
* Raise `ValueError` immediately if inputs fall outside these ranges.

#### [NEW] [simulation.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/scenario_engine/simulation.py)
* Implement `simulate_cashflow_scenario(business_id, as_of_month, inflow_change_pct, outflow_change_pct, collection_delay_change_days, payroll_change_pct, debt_service_change_pct)`.
* Calculate simulated cash flows deterministically.
* **Risk Score Projection:** Reconstruct the point-in-time feature vector by replacing month $T$'s values with simulated values, then score the vector using the cached ML model. Preserve unaffected baseline features (e.g., late invoice rates, historical overdrafts) and document this scoring limitation.

#### [NEW] [sensitivity.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/scenario_engine/sensitivity.py)
* Implement `run_one_way_sensitivity(business_id, as_of_month, variable, values)`.
* Support variations on `inflow_change_pct`, `outflow_change_pct`, and `collection_delay_change_days` (up to 10 points).

#### [MODIFY] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/scenario_engine/__init__.py)
* Expose `simulate_cashflow_scenario` and `run_one_way_sensitivity`.

---

### Component 4: Intervention Engine

Computes draft recommendation options based on policy thresholds and calculated stress indicators.

#### [NEW] [schemas.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/intervention_engine/schemas.py)
* Define Pydantic models:
  * `InterventionRecommendation`: action name, priority, and description.
  * `InterventionPlan`: business details, overall risk tier, evidence codes, recommendations list, priority, rationale codes, and HITL approval flags.

#### [NEW] [rules.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/intervention_engine/rules.py)
* Define the policy rule matrix mapping risk scores, RAG tiers, benchmark gaps, current delinquency, and scenario outcomes to allowed draft recommendations.
* Ensure watchlist-related proposals set `human_approval_required = True`.
* Strictly exclude prohibited actions (like automatic credit-limit reductions or email notifications).

#### [NEW] [recommendations.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/intervention_engine/recommendations.py)
* Implement `draft_intervention_plan(business_id, as_of_month, risk_result, benchmark_result, scenario_result=None)`.

#### [MODIFY] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/intervention_engine/__init__.py)
* Expose `draft_intervention_plan`.

---

### Component 5: Structured Agent Tools & Registry

Wraps the core engines inside schema-enforced, safe interfaces for future Agent consumption.

#### [NEW] [portfolio.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/portfolio.py)
* Implement `get_portfolio_snapshot_tool(as_of_month, industry=None, region=None, limit=100)`. Enrich with risk scores using cached model. Limit dynamic scoring to 100 entries.

#### [NEW] [business.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/business.py)
* Implement `get_business_history_tool` and `check_business_data_quality_tool`.

#### [NEW] [risk.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/risk.py)
* Implement `score_cashflow_risk_tool`.

#### [NEW] [benchmark.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/benchmark.py)
* Implement `compare_with_peers_tool`.

#### [NEW] [scenario.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/scenario.py)
* Implement `simulate_cashflow_scenario_tool`.

#### [NEW] [intervention.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/intervention.py)
* Implement `draft_intervention_plan_tool` with optional scenario calculation inputs.

#### [NEW] [registry.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/registry.py)
* Maintain the registry dictionary.
* Define `get_tool_registry()`, `get_tool_by_name(name)`, and `list_tool_metadata()`.
* Ensure registry checks exclude forbidden operations (arbitrary SQL execution, writing to source DB, email triggers).

#### [MODIFY] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/tools/__init__.py)
* Expose tool registry and wrappers.

---

## Verification Plan

### Automated Tests
Implement unit tests in the directories:
* `tests/unit/benchmark_engine/`
* `tests/unit/scenario_engine/`
* `tests/unit/intervention_engine/`
* `tests/unit/tools/`

Implement integration tests:
* `tests/integration/test_benchmark_engine_real_db.py`
* `tests/integration/test_scenario_engine_real_db.py`
* `tests/integration/test_tool_workflows.py`

Run test suites using:
```bash
python -m pytest tests/unit/benchmark_engine -q
python -m pytest tests/unit/scenario_engine -q
python -m pytest tests/unit/intervention_engine -q
python -m pytest tests/unit/tools -q
python -m pytest tests/integration/test_benchmark_engine_real_db.py -q
python -m pytest tests/integration/test_scenario_engine_real_db.py -q
python -m pytest tests/integration/test_tool_workflows.py -q
```

### Validation Scripts
Execute scripts to verify real DB queries and tool registries:
```bash
python scripts/validate_business_engines.py
python scripts/validate_tools.py
```

### Manual Verification
* Inspect generated artifacts:
  * [business_engines_design.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/business_engines_design.md)
  * [business_engines_validation.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/business_engines_validation.md)
  * [tool_registry.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/tool_registry.md)
  * [business_engines_test_output.txt](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/test_results/business_engines_test_output.txt)
* Verify that DuckDB file timestamp and row counts remain unchanged.
