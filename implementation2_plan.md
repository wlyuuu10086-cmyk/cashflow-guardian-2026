# Implementation Plan - P0 Read-Only Data Engine

This plan describes the implementation of the read-only Data Engine for **CashFlow Guardian**. The Data Engine acts as the central data access and transformation layer, querying DuckDB, validating inputs, checking data quality, calculating financial metrics, and building feature vectors for downstream risk scoring.

## User Review Required

> [!IMPORTANT]
> **Pydantic Dependency Missing:**
> Pydantic is not installed in the current environment. To ensure maximum robustness and portability without silent installations, we propose two options:
> 1. Use standard Python `dataclasses` (with custom deserialization/validation logic) as a fallback.
> 2. Approve the installation of `pydantic` in this environment.
> We have designed the implementation plan to use **typed dataclasses** as a temporary fallback to allow execution immediately. We will document this deviation in the validation report.

> [!IMPORTANT]
> **Source Database Safety (Read-Only):**
> We will open the DuckDB connection explicitly with `read_only=True` using the relative database path configured in `config/database.yaml`. We will implement a SQL safety guard that parses and blocks queries referencing `business_monthly_outcomes` or containing `future_60d_*` fields during normal inference.

## Open Questions

There are no major open questions, but we would like user confirmation on:
- Do you prefer using native typed dataclasses as a robust fallback, or should we install `pydantic`? (We recommend native typed dataclasses to keep dependencies minimal, and will proceed with them).

## Proposed Changes

We will implement the Data Engine under `src/cashflow_guardian/data_engine/` and add complete unit and integration tests.

### Component: Data Engine Package (`src/cashflow_guardian/data_engine/`)

#### [NEW] [connection.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/connection.py)
Implements centralized DuckDB connection logic.
- Resolves database path relative to repository root using `pathlib` and `config/database.yaml`.
- Opens connection with `read_only=True`.
- Exposes `get_database_path()`, `get_readonly_connection()`, and `check_database_health()`.
- Implements `QuerySafetyError` and safety validation on queries to ensure no lookahead table or columns are accessed.

#### [NEW] [schemas.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/schemas.py)
Defines the required data contracts from `specs/data_contracts.yaml` using typed dataclasses (as a fallback for Pydantic):
- `ProvenanceMetadata`
- `DatabaseHealthResult`
- `DataQualityResult`
- `BusinessMonthlyMetric`
- `BusinessHistoryResult`
- `PortfolioBusinessRecord`
- `PortfolioSnapshotResult`
- `PeerBenchmarkResult`
- `FeatureVectorResult`

#### [NEW] [validators.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/validators.py)
Enforces constraints on inputs:
- `validate_business_id(business_id, conn)`: Verifies format (`BUS_\d{3,4}`) and checks database presence.
- `validate_as_of_month(as_of_month, conn)`: Verifies format (`YYYY-MM`), checks boundary limits (`2024-01` to `2025-12`), and confirms data availability.
- Exposes specific typed validation exceptions: `ValidationError`, `InvalidBusinessIDError`, `InvalidMonthError`, `OutOfBoundaryMonthError`.

#### [NEW] [metrics.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/metrics.py)
Contains pure, type-hinted, and docstring-documented mathematical functions:
- `net_cash_flow(inflow, outflow)`
- `repayment_burden_ratio(scheduled_debt_service, inflow)`
- `payroll_burden_ratio(payroll_amount, inflow)`
- `cash_flow_volatility(net_cash_flows)`
- `percentage_change(old_val, new_val)`
- `rolling_mean(values)`
- `consecutive_negative_cash_flow_months(net_cash_flows)`
- `benchmark_absolute_gap(observed, benchmark)`
- `benchmark_percentage_gap(observed, benchmark)`
All functions handle divide-by-zero, negative numbers, and null behaviors safely.

#### [NEW] [provenance.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/provenance.py)
Helper function to automatically construct `ProvenanceMetadata` for all outputs, recording:
- `source_tables`
- `as_of_month`
- `query_timestamp`
- `row_count`
- `future_data_used = False`
- `warnings`

#### [NEW] [queries.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/queries.py)
Houses pre-defined SQL query constants and query execution helper functions.
- NO raw SQL execution function is exposed.
- All query definitions are static parameterized SQL statements.
- Includes queries for fetching portfolio snapshot, business history, peer benchmark, and data quality metrics.
- Enforces point-in-time filtering (`month <= ?` or equivalent).

#### [NEW] [quality.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/quality.py)
Implements `check_business_data_quality(business_id, as_of_month)` checking:
- Business existence, month existence, snapshot availability, history completeness (at least 3 months of snapshots).
- Duplicate rows, missing key fields, incomplete current-month evidence.
- Returns `DataQualityResult`.

#### [NEW] [repository.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/repository.py)
Implements retrieval functions:
- `get_business_history(business_id, as_of_month, months=6)`
- `get_portfolio_snapshot(as_of_month, industry=None, region=None, limit=1500)`
- `get_peer_benchmark(business_id, as_of_month)`

#### [NEW] [features.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/features.py)
Implements `build_point_in_time_features(business_id, as_of_month)`:
- Queries history up to `as_of_month`.
- Calculates current, rolling 3-month averages, and volatility features.
- Computes peer gaps.
- Enforces zero future outcomes usage and sets `future_data_used = False`.

#### [MODIFY] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/data_engine/__init__.py)
Exposes the clean public interface:
- `check_database_health`
- `check_business_data_quality`
- `get_business_history`
- `get_portfolio_snapshot`
- `get_peer_benchmark`
- `build_point_in_time_features`
- `validate_business_id`
- `validate_as_of_month`
- Database and validation exceptions.

---

### Component: Tests (`tests/`)

#### [NEW] [conftest.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/conftest.py)
Sets up test fixtures:
- Configures test environments and temporary/mock test database connections.

#### [NEW] [test_connection.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_connection.py)
Verifies database path resolution, read-only connectivity, required tables check, and write protection.

#### [NEW] [test_validators.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_validators.py)
Tests input validation limits, invalid IDs, malformed months, out-of-boundary months, and history bounds.

#### [NEW] [test_metrics.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_metrics.py)
Tests metric functions under normal and edge conditions (zero, negative, null).

#### [NEW] [test_repository.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_repository.py)
Tests business history and portfolio snapshot queries against point-in-time constraints.

#### [NEW] [test_features.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_features.py)
Tests that point-in-time features contain no future leakages, name-value alignment, and rolling calculations.

#### [NEW] [test_quality.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_quality.py)
Tests business data quality logic (blocked vs warnings vs complete cases).

#### [NEW] [test_provenance.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/data_engine/test_provenance.py)
Tests correctness of provenance outputs.

#### [NEW] [test_data_engine_real_db.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/integration/test_data_engine_real_db.py)
Integration tests running queries on the real DuckDB database.

---

### Component: Scripts (`scripts/`)

#### [NEW] [validate_data_engine.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/scripts/validate_data_engine.py)
Run-script executing full checks against the real database and printing details.

---

### Component: Artifacts (`artifacts/`)

#### [NEW] [data_engine_design.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/data_engine_design.md)
Contains findings from database schema and view audits, and documents data engine structure and formulas.

---

## Verification Plan

### Automated Tests
We will execute unit and integration tests using `pytest`:
```bash
pytest tests/unit/data_engine/
pytest tests/integration/test_data_engine_real_db.py
```

We will also run the validation script:
```bash
python scripts/validate_data_engine.py
```

### Manual Verification
- Verify that DuckDB file modification timestamps and row counts do not change during test suite runs.
- Manually inspect the validation script output in `artifacts/test_results/data_engine_test_output.txt`.
- Save validation findings into `artifacts/data_engine_validation.md`.
