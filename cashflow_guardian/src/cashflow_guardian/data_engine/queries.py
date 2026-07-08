from .connection import validate_query_safety, validate_no_write

# Predefined Parameterized Query Constants

GET_BUSINESS_SNAPSHOTS_UP_TO_MONTH = """
SELECT 
    month,
    opening_cash_balance_proxy,
    ending_cash_balance_proxy,
    avg_daily_balance_proxy,
    overdraft_days_proxy,
    transaction_count,
    cash_inflow_observed,
    cash_outflow_observed,
    net_cash_flow_observed,
    invoice_count,
    invoice_amount_total,
    avg_days_to_pay,
    late_invoice_rate,
    payroll_amount,
    employee_count,
    scheduled_debt_service,
    actual_debt_service,
    max_dpd,
    available_credit_drawn_ratio
FROM business_monthly_snapshots
WHERE business_id = ? AND month <= ?
ORDER BY month ASC
"""

GET_BUSINESS_HISTORY_QUERY = """
SELECT 
    month,
    cash_inflow_observed AS cash_inflow,
    cash_outflow_observed AS cash_outflow,
    net_cash_flow_observed AS net_cash_flow,
    ending_cash_balance_proxy AS ending_balance,
    avg_daily_balance_proxy AS average_daily_balance,
    overdraft_days_proxy AS overdraft_days,
    invoice_count,
    avg_days_to_pay,
    late_invoice_rate,
    payroll_amount,
    employee_count,
    scheduled_debt_service,
    actual_debt_service,
    max_dpd AS maximum_days_past_due,
    available_credit_drawn_ratio AS credit_utilization_ratio
FROM business_monthly_snapshots
WHERE business_id = ? AND month <= ?
ORDER BY month DESC
LIMIT ?
"""

GET_PORTFOLIO_SNAPSHOT_QUERY = """
SELECT 
    c.business_id,
    c.business_name,
    c.industry,
    c.region,
    c.revenue_band,
    c.relationship_manager_id,
    s.cash_inflow_observed AS cash_inflow,
    s.cash_outflow_observed AS cash_outflow,
    s.net_cash_flow_observed AS net_cash_flow,
    s.ending_cash_balance_proxy AS ending_cash_balance,
    s.avg_days_to_pay AS average_collection_days,
    s.late_invoice_rate,
    s.payroll_amount,
    s.scheduled_debt_service,
    s.max_dpd AS maximum_days_past_due,
    s.available_credit_drawn_ratio AS credit_utilization_ratio
FROM business_monthly_snapshots s
JOIN business_customers c ON s.business_id = c.business_id
WHERE s.month = ?
"""

GET_BUSINESS_PEER_INFO_QUERY = """
SELECT industry, industry_id FROM business_customers WHERE business_id = ?
"""

GET_INDUSTRY_BENCHMARK_QUERY = """
SELECT 
    industry_id,
    industry,
    benchmark_margin,
    benchmark_cash_flow_volatility,
    benchmark_collection_days,
    benchmark_repayment_burden_pct,
    payroll_intensity
FROM industry_benchmark
WHERE industry_id = ?
"""

# Compile-time validation: Ensure all predefined queries are safe and do not contain write commands
PREDEFINED_QUERIES = [
    GET_BUSINESS_SNAPSHOTS_UP_TO_MONTH,
    GET_BUSINESS_HISTORY_QUERY,
    GET_PORTFOLIO_SNAPSHOT_QUERY,
    GET_BUSINESS_PEER_INFO_QUERY,
    GET_INDUSTRY_BENCHMARK_QUERY
]

for query in PREDEFINED_QUERIES:
    validate_query_safety(query)
    validate_no_write(query)
