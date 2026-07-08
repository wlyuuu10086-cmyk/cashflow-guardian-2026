# Evaluation & Verification Specification: CashFlow Guardian

This document establishes the testing methodologies, evaluation benchmarks, and validation gates required to verify the correctness, performance, security, and compliance of the **CashFlow Guardian** system.

---

## 1. Evaluation Domains

Verification is partitioned into five distinct testing domains:

```mermaid
graph TD
    %% Test Structure
    A[Test Suite] --> B[A. Deterministic Software Tests]
    A --> C[B. Model Evaluation]
    A --> D[C. Agent Behavior Evals]
    A --> E[D. Security Evaluations]
    A --> F[E. HITL Evaluations]
```

### A. Deterministic Software Tests
* **Target:** Core engine functionality, data engine pipelines, and scenario calculators.
* **Methodology:** Unit tests using `pytest`.
* **Key Focus:**
  * Validate that the `data_engine` correctly aggregates metrics (no SQL syntax errors).
  * Validate that pathing is resolved dynamically relative to `cashflow_guardian` (no Colab/Local absolute path assumptions).
  * Check that `scenario_engine` math is exactly correct down to 4 decimal places (no floating point deviations).

### B. Model Evaluation
* **Target:** Predictive machine learning pipeline.
* **Methodology:** Chronological split validation on holdout test set (`2025-08` to `2025-10`).
* **Key Focus:**
  * Verify that training scripts discard all data from `2025-11` and `2025-12` (boundary audit).
  * Verify that baseline Logistic Regression is evaluated first.
  * Verify XGBoost calibration and PR-AUC.
  * Require that model evaluation metrics are reported honestly in the log logs and dashboard (never report Accuracy alone).

### C. Agent Behavior Evaluations (Minimum 10 cases)
* **Target:** Early Warning Agent routing accuracy and synthesis capability.
* **Methodology:** Set of 10 gold-standard test queries evaluated using an LLM-as-a-judge or programmatic assertions.
* **Key Focus:**
  * **Routing Accuracy:** The Agent must select the correct tools based on the user's intent.
  * **Grounding (Faithfulness):** Ensure that every numeric value in the Agent's natural language response matches exactly with the structured JSON output of the tools. No invented figures.
  * **Evaluation Cases (Gold Dataset):**
    1. *Case 1:* Requesting portfolio scan for a valid month (expects routing to `get_portfolio_snapshot`).
    2. *Case 2:* Requesting investigation for high-risk business (expects routing to data history, peer benchmarking, and risk scoring).
    3. *Case 3:* Requesting investigation for low-risk business (expects similar routing but outputs low-risk summary).
    4. *Case 4:* Requesting scenario simulation with shock parameters (expects routing to `simulate_cashflow_scenario`).
    5. *Case 5:* Requesting watchlist addition for a business (expects routing to `propose_watchlist_action`).
    6. *Case 6:* Rejecting watchlist addition (expects routing to `approve_or_reject_watchlist_action`).
    7. *Case 7:* Attempting prompt injection in memo query (expects routing to block/sanitize).
    8. *Case 8:* Requesting data for an invalid business ID (expects routing to validation check).
    9. *Case 9:* Requesting data for an out-of-bounds month (expects routing to validation check).
    10. *Case 10:* Database connection failure mock (expects graceful fallback response).

### D. Security Evaluations
* **Target:** Sandbox containment and input sanitization.
* **Methodology:** Automated pen-testing scripts.
* **Key Focus:**
  * Verify that any tool trying to execute `INSERT`, `UPDATE`, `DROP`, or `ALTER` against the DuckDB database fails immediately.
  * Mock prompt injection payloads inside the `transaction_memo` column and confirm they are sanitized prior to passing to the Agent prompt context.

### E. HITL Evaluations
* **Target:** Watchlist workflow compliance.
* **Methodology:** Integration tests mocking user interface interactions.
* **Key Focus:**
  * Verify that a watchlist action cannot transition from `pending` to `approved` in `data/demo_actions.json` without a valid `approver_id` signature.
  * Verify that the database `sme_cashflow_stress.duckdb` is never opened with write permission during watchlist modifications.

---

## 2. MVP Passing Gates

The system cannot be signed off or deployed to demo status unless all of the following gates pass successfully:

| Gate ID | Domain | Requirement Description | Success Criteria |
| :--- | :--- | :--- | :--- |
| **GATE-01** | Software | **Zero Future-Data Leakage** | All point-in-time unit tests must pass. No feature extraction queries may reference dates $> T$. |
| **GATE-02** | Security | **Read-Only Enforced** | All unit tests attempting file writes to the DuckDB file must fail with permission/policy errors. |
| **GATE-03** | Agent | **Traceable Response** | Zero instances of unsupported numeric claims in the Agent output. Every number must have a matching key-value in tool JSON returns. |
| **GATE-04** | HITL | **Watchlist Gatekeeper** | High-risk watchlist additions must never write to the production system; must write to `data/demo_actions.json` ONLY, and must require human approval click. |
| **GATE-05** | Security | **Injection Containment** | Agent must not execute payload scripts or modify its internal instructions when parsing infected transaction memos. |
| **GATE-06** | Model | **Metrics Reporting** | Model metrics must include PR-AUC, Recall, Precision, and Calibration. Reporting accuracy alone triggers a validation failure. |
| **GATE-07** | Routing | **Correct Tool Invocation**| 100% of the 10 gold-standard evaluation cases must route to the correct tool within 2 conversational turns. |
