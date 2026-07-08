# CashFlow Guardian: Policy Validation Report

This document reports the verification results of the policy engine and Human-in-the-Loop (HITL) workflows validated by `scripts/validate_policy_engine.py` and `scripts/validate_hitl_workflow.py`.

---

## 1. Policy Engine & RBAC Rule Verification

Using `scripts/validate_policy_engine.py`, the following scenarios were executed:

### Scenario 1: Approved portfolio read request by Relationship Manager
- Role: `relationship_manager`
- Tool: `get_portfolio_snapshot`
- Result: **Allowed: True**
- Policy Code: `['POLICY_TOOL_ALLOWED']`

### Scenario 2: Denied portfolio read request by Administrator
- Role: `administrator`
- Tool: `get_portfolio_snapshot`
- Result: **Allowed: False (Blocked)**
- Policy Code: `['POLICY_PERMISSION_MISSING']`
- Warning: `Role 'administrator' does not possess required permission 'portfolio.read'.`

### Scenario 3: Unknown tool request
- Role: `relationship_manager`
- Tool: `unknown_tool_xyz`
- Result: **Allowed: False (Blocked)**
- Policy Code: `['POLICY_TOOL_DENIED']`
- Warning: `Tool is not registered in the system registry.`

### Scenario 4: Forbidden database write argument
- Role: `relationship_manager`
- Tool: `get_business_history`
- Arguments: `sql="DROP TABLE repayments"`
- Result: **Allowed: False (Blocked)**
- Policy Code: `['POLICY_ARBITRARY_SQL_BLOCKED']`
- Warning: `Action blocked: Arbitrary SQL execution is prohibited.`

---

## 2. Human-in-the-Loop (HITL) Watchlist Workflow Verification

Using `scripts/validate_hitl_workflow.py`, end-to-end proposal creation, validation, and review were verified:

1. **Information Querying**: Retrieved cashflow risk score (`0.1685`, tier `RED`), peer benchmark, and intervention drafts.
2. **Watchlist Proposal Initiation**: Relationship Manager (`RM_John`) proposed adding business customer `B00001` to the watchlist. Proposal `proposal_f8c570baa1664157` was created in the `pending` state.
3. **Self-Approval Prevention**: `RM_John` attempted to approve their own proposal. The system blocked the attempt successfully:
   - Error: `Policy violation (POLICY_SELF_APPROVAL_DENIED): Conflict of interest: Proposer cannot review their own proposal.`
4. **Authorized Review**: Risk Manager `Mgr_Sarah` reviewed and approved the proposal. The proposal state transitioned to `approved`, and business `B00001` was added to the active watchlist.

---

## 3. Strict Database Immutability Verification

During the execution of the HITL watchlist workflow, the source DuckDB database was monitored before and after to ensure that no mutations took place:

### Database Metadata Comparison
- **File Size**:
  - Before: `17313792` bytes
  - After: `17313792` bytes (Delta: `0` bytes)
- **Table Row Counts**:
  - `business_customers`: `1500` (Before) $\rightarrow$ `1500` (After)
  - `bank_transactions`: `482790` (Before) $\rightarrow$ `482790` (After)
  - `invoices`: `90000` (Before) $\rightarrow$ `90000` (After)
  - `loans`: `2800` (Before) $\rightarrow$ `2800` (After)
  - `repayments`: `46790` (Before) $\rightarrow$ `46790` (After)
  - `payroll`: `36000` (Before) $\rightarrow$ `36000` (After)
  - `business_monthly_snapshots`: `36000` (Before) $\rightarrow$ `36000` (After)
  - `industry_benchmark`: `12` (Before) $\rightarrow$ `12` (After)
  - `region_dim`: `6` (Before) $\rightarrow$ `6` (After)
  - `region_macro_index`: `144` (Before) $\rightarrow$ `144` (After)
  - `relationship_managers`: `60` (Before) $\rightarrow$ `60` (After)

- Result: **Immutability verified at 100% unchanged.** All watchlist actions targets `data/demo_actions.json` without modifying the source database.
