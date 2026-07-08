import math
from typing import List, Optional

def net_cash_flow(inflow: Optional[float], outflow: Optional[float]) -> float:
    """Calculates net cash flow = inflow - outflow.
    
    Treats None values as 0.0.
    """
    inf = inflow if inflow is not None else 0.0
    outf = outflow if outflow is not None else 0.0
    return inf - outf

def repayment_burden_ratio(scheduled_debt_service: Optional[float], inflow: Optional[float]) -> Optional[float]:
    """Calculates the ratio of scheduled debt service to cash inflow.
    
    Returns None if scheduled_debt_service or inflow is None, or if inflow is zero.
    """
    if scheduled_debt_service is None or inflow is None:
        return None
    if inflow == 0.0:
        return None
    return scheduled_debt_service / inflow

def payroll_burden_ratio(payroll_amount: Optional[float], inflow: Optional[float]) -> Optional[float]:
    """Calculates the ratio of payroll amount to cash inflow.
    
    Returns None if payroll_amount or inflow is None, or if inflow is zero.
    """
    if payroll_amount is None or inflow is None:
        return None
    if inflow == 0.0:
        return None
    return payroll_amount / inflow

def cash_flow_volatility(net_cash_flows: List[Optional[float]]) -> Optional[float]:
    """Calculates the sample standard deviation of net cash flows.
    
    Returns None if there are fewer than 2 valid observations.
    """
    valid = [x for x in net_cash_flows if x is not None]
    if len(valid) < 2:
        return None
    mean = sum(valid) / len(valid)
    variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1)
    return math.sqrt(variance)

def percentage_change(current_value: Optional[float], previous_value: Optional[float]) -> Optional[float]:
    """Calculates the percentage change of current_value compared to previous_value.
    
    Formula: (current_value - previous_value) / abs(previous_value)
    
    Returns None if either value is None, or if previous_value is zero.
    """
    if current_value is None or previous_value is None:
        return None
    if previous_value == 0.0:
        return None
    return (current_value - previous_value) / abs(previous_value)

def rolling_mean(values: List[Optional[float]]) -> Optional[float]:
    """Calculates the rolling arithmetic mean of the provided values.
    
    Filters out None values. Returns None if there are no valid values.
    """
    valid = [x for x in values if x is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)

def consecutive_negative_cash_flow_months(net_cash_flows: List[Optional[float]]) -> int:
    """Counts the consecutive number of negative cash flow months starting from the end
    (most recent month) and moving backwards.
    
    None or positive values stop the streak.
    """
    streak = 0
    for val in reversed(net_cash_flows):
        if val is not None and val < 0.0:
            streak += 1
        else:
            break
    return streak

def benchmark_absolute_gap(observed: Optional[float], benchmark: Optional[float]) -> Optional[float]:
    """Calculates the absolute difference: observed - benchmark.
    
    Returns None if either value is None.
    """
    if observed is None or benchmark is None:
        return None
    return observed - benchmark

def benchmark_percentage_gap(observed: Optional[float], benchmark: Optional[float]) -> Optional[float]:
    """Calculates the percentage gap relative to benchmark: (observed - benchmark) / abs(benchmark).
    
    Returns None if either value is None, or if benchmark is zero.
    """
    if observed is None or benchmark is None:
        return None
    if benchmark == 0.0:
        return None
    return (observed - benchmark) / abs(benchmark)
