# Business Engines Design Specification

This document defines the mathematical models, formulas, decision rules, and architecture for the **Benchmark Engine**, **Scenario Engine**, and **Intervention Engine**.

---

## 1. Benchmark Engine

### Peer-Group Selection Logic
The selection of the peer group is designed to be point-in-time safe and dynamically selects the narrowest valid peer group to compare a given business:
1. **Industry and Revenue Band (Preferred):** Returns all other businesses in the same industry and annual revenue band as the target business that have a snapshot in `as_of_month`.
2. **Industry Only (Fallback):** If the preferred peer group size is less than `min_peer_count` (default: 5), falls back to all other businesses in the same industry with a snapshot in `as_of_month`.
3. **Official Industry Benchmarks (Final Fallback):** If the industry-wide peer count is less than `min_peer_count`, falls back to the static reference values in the `industry_benchmark` table.

> [!NOTE]
> The target business is strictly **excluded** from its own peer distribution count, median, and percentile rank calculations.

### Metrics and Gaps Formulas
* **Cash-Flow Volatility:** Sample standard deviation of the last 6 months net cash flow observations.
* **Average Collection Days:** Observed `avg_days_to_pay` in the target month.
* **Late Invoice Rate:** Observed `late_invoice_rate` in the target month.
* **Repayment Burden Ratio:** `scheduled_debt_service / cash_inflow_observed`.
* **Payroll Burden Ratio:** `payroll_amount / cash_inflow_observed`.
* **Credit Utilization:** Observed `available_credit_drawn_ratio` in the target month.
* **Overdraft Days:** Observed `overdraft_days_proxy` in the target month.
* **Three-Month Net Cash-Flow Trend:** $NetCashFlow_T - NetCashFlow_{T-2}$.

For each metric:
* $\text{Absolute Gap} = Value_{business} - Value_{peer}$
* $\text{Percentage Gap} = \frac{Value_{business} - Value_{peer}}{|Value_{peer}|}$ (where $Value_{peer} \neq 0$)
* $\text{Percentile Rank} = \frac{\text{Count}(P_i \le Value_{business})}{\text{Total Peers}} \times 100$

---

## 2. Scenario Engine

### Assumptions and Validations
Input parameters must satisfy the following boundaries:
* `inflow_change_pct`: $[-100.0\%, +200.0\%]$
* `outflow_change_pct`: $[-100.0\%, +200.0\%]$
* `collection_delay_change_days`: $[-60, +180 \text{ days}]$
* `payroll_change_pct`: $[-100.0\%, +200.0\%]$
* `debt_service_change_pct`: $[-100.0\%, +200.0\%]$

### Collection Delay Deterministic Formula
To translate collection delay changes into a cash-flow impact on monthly inflow:
* **Scenario Horizon:** 30 days (1 calendar month).
* **Deferred Inflow Formula:**
  $$\text{Deferred Inflow} = \text{invoice\_amount\_total} \times \min\left(1.0, \frac{\text{collection\_delay\_change\_days}}{30.0}\right)$$
* **Simulated Cash Inflow:**
  $$\text{Simulated Inflow} = \max\left(0.0, \text{baseline\_inflow} \times (1 + \text{inflow\_change\_pct}) - \text{Deferred Inflow}\right)$$

### Derived Feature Re-computation
When running scenario projections, the system does not simply replace target month values. It builds a simulated 6-month historical vector by replacing month $T$'s observed values with simulated values and recomputing:
* `cash_inflow_3m_avg`
* `cash_inflow_mom_change`
* `net_cash_flow_3m_avg`
* `net_cash_flow_6m_volatility`
* `repayment_burden_3m_avg`
* `payroll_burden_3m_avg`

These recomputed features are then fed into the cached model to compute a simulated risk score and tier.

---

## 3. Intervention Engine

### Rule Mapping Matrix

| Risk Tier / Trigger | Recommended Actions | Priority | Approval | Prohibited Actions |
| :--- | :--- | :---: | :---: | :--- |
| **RED Risk Tier** | `contact relationship manager for manual review`, `propose demonstration watchlist review` | High | Yes (Watchlist) | automatic credit reduction, automatic collections, sending direct email |
| **AMBER Risk Tier** | `increase monitoring frequency`, `request updated cash-flow information` | Medium | No | same as above |
| **GREEN Risk Tier** | `continue routine monitoring` | Low | No | same as above |
| **Repayment Burden > 25%** | `review repayment schedule` | Medium | No | same as above |
| **Collection delay > 15 days** | `verify large outstanding invoices` | Medium | No | same as above |
| **Active Overdraft / Decline** | `assess short-term liquidity support eligibility` | Medium | No | same as above |
| **Scenario Deterioration (to RED)**| `assess short-term liquidity support eligibility` | High | No | same as above |

---

## 4. Limitations
* **Heuristics on Overdraft Days:** Overdraft days are not dynamically modeled in scenario projections and are held at baseline.
* **Late Invoice Rate Correlation:** The scenario simulation does not synthesize new customer invoice statuses, keeping late invoice rates at baseline.
* **Horizon Limits:** Calculations assume a static 30-day billing cycle for receivables aging projections.
