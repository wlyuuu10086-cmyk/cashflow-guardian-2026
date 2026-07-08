import os
import sys
from pathlib import Path
import json

# Add src to python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.append(str(repo_root / "src"))

import duckdb
from cashflow_guardian.benchmark_engine.comparison import compare_business_with_peers
from cashflow_guardian.scenario_engine.simulation import simulate_cashflow_scenario
from cashflow_guardian.scenario_engine.sensitivity import run_one_way_sensitivity
from cashflow_guardian.intervention_engine.recommendations import draft_intervention_plan
from cashflow_guardian.risk_engine.scoring import score_cashflow_risk

def main():
    print("======================================================================")
    print("CASHFLOW GUARDIAN: BUSINESS ENGINES VALIDATION")
    print("======================================================================")
    
    # 1. Resolve database path and query a valid business/month
    db_path = repo_root / "sme_cashflow_stress_project" / "data" / "sme_cashflow_stress.duckdb"
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
        
    print(f"Connecting to database: {db_path}")
    conn = duckdb.connect(str(db_path), read_only=True)
    
    # Fetch a business that is high-risk to showcase RED tier and watchlist approvals
    # E.g., B00001 (which we know is high risk or has high volatility) or dynamically select
    biz_row = conn.execute(
        """
        SELECT s.business_id, s.month 
        FROM business_monthly_snapshots s
        JOIN business_customers c ON s.business_id = c.business_id
        WHERE s.month = '2025-06'
        ORDER BY s.overdraft_days_proxy DESC, s.late_invoice_rate DESC
        LIMIT 1
        """
    ).fetchone()
    
    if not biz_row:
        print("Error: No snapshots found for month 2025-06")
        sys.exit(1)
        
    business_id, month = biz_row
    print(f"Selected target client: {business_id} as of {month}")
    conn.close()
    
    # 2. Benchmark Comparison
    print("\n--- Running Peer Benchmark Comparison ---")
    bench_res = compare_business_with_peers(business_id, month)
    print(f"Peer Group Method: {bench_res.peer_group.method}")
    print(f"Peer Count: {bench_res.peer_group.peer_count}")
    print(f"Industry: {bench_res.peer_group.industry}")
    print("Metric Gaps:")
    for metric, comp in bench_res.metrics.items():
        print(f"  - {metric}: Biz={comp.business_value}, Peer={comp.peer_value}, Gap={comp.absolute_gap}, Direction={comp.direction}")
        
    # 3. No-Change Scenario (Should match baseline)
    print("\n--- Running No-Change Scenario Simulation ---")
    no_change_res = simulate_cashflow_scenario(
        business_id=business_id,
        as_of_month=month,
        inflow_change_pct=0.0,
        outflow_change_pct=0.0,
        collection_delay_change_days=0.0
    )
    print(f"Baseline Risk Score: {no_change_res.baseline.risk_score:.4f} ({no_change_res.baseline.risk_tier})")
    print(f"Simulated Risk Score: {no_change_res.simulated.risk_score:.4f} ({no_change_res.simulated.risk_tier})")
    score_diff = abs(no_change_res.baseline.risk_score - no_change_res.simulated.risk_score)
    print(f"Score Difference: {score_diff:.6f} (No-change comparison)")
    
    # 4. Downside Scenario (Inflow drop 20%, Collection delay 15 days)
    print("\n--- Running Downside Scenario Simulation ---")
    downside_res = simulate_cashflow_scenario(
        business_id=business_id,
        as_of_month=month,
        inflow_change_pct=-20.0,
        outflow_change_pct=10.0,
        collection_delay_change_days=15.0
    )
    print(f"Simulated Inflow: {downside_res.simulated.cash_inflow:,.2f} (Baseline: {downside_res.baseline.cash_inflow:,.2f})")
    print(f"Amount Deferred: {downside_res.collection_delay_details.get('amount_of_inflow_deferred'):,.2f}")
    print(f"Simulated Risk Score: {downside_res.simulated.risk_score:.4f} ({downside_res.simulated.risk_tier})")
    print(f"Risk Score Change: {downside_res.risk_score_change * 100.0:+.2f}%")
    print(f"Risk Tier Change: {downside_res.risk_tier_change}")
    
    # 5. Sensitivity Results
    print("\n--- Running One-Way Sensitivity Analysis ---")
    sens_vals = [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0]
    sens_res = run_one_way_sensitivity(
        business_id=business_id,
        as_of_month=month,
        variable="inflow_change_pct",
        values=sens_vals
    )
    print("Inflow Shock Sensitivity:")
    for r in sens_res:
        print(f"  Shock: {r['value']:+5.1f}% | Net Cash Flow: {r['simulated_net_cash_flow']:+11,.2f} | Score: {r['simulated_risk_score']:.4f} ({r['simulated_risk_tier']})")
        
    # 6. Draft Intervention Plan
    print("\n--- Running Draft Intervention Plan ---")
    risk_res = score_cashflow_risk(business_id, month)
    plan = draft_intervention_plan(business_id, month, risk_res, bench_res, downside_res)
    print(f"Plan Priority: {plan.priority.upper()}")
    print(f"Evidence Codes: {plan.evidence_codes}")
    print(f"Human Approval Required: {plan.human_approval_required}")
    print("Recommended Draft Actions:")
    for act in plan.recommended_draft_actions:
        print(f"  - [{act.priority.upper()}] {act.action}: {act.description}")
    print("Prohibited Actions (Security Filter):")
    for act in plan.prohibited_actions:
        print(f"  - [BLOCKED] {act}")
        
    print("\n======================================================================")
    print("VALIDATION COMPLETED SUCCESSFULLY")
    print("======================================================================")

if __name__ == "__main__":
    main()
