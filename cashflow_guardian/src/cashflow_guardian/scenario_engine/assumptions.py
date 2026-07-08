def validate_assumptions(
    inflow_change_pct: float,
    outflow_change_pct: float,
    collection_delay_change_days: float,
    payroll_change_pct: float,
    debt_service_change_pct: float
) -> None:
    """Validates that assumptions are within safe MVP ranges.
    
    Raises ValueError with descriptive messages on failures.
    """
    if not (-100.0 <= inflow_change_pct <= 200.0):
        raise ValueError(f"Inflow change pct must be between -100.0 and +200.0, got {inflow_change_pct}")
        
    if not (-100.0 <= outflow_change_pct <= 200.0):
        raise ValueError(f"Outflow change pct must be between -100.0 and +200.0, got {outflow_change_pct}")
        
    if not (-60.0 <= collection_delay_change_days <= 180.0):
        raise ValueError(f"Collection delay change days must be between -60.0 and +180.0, got {collection_delay_change_days}")
        
    if not (-100.0 <= payroll_change_pct <= 200.0):
        raise ValueError(f"Payroll change pct must be between -100.0 and +200.0, got {payroll_change_pct}")
        
    if not (-100.0 <= debt_service_change_pct <= 200.0):
        raise ValueError(f"Debt service change pct must be between -100.0 and +200.0, got {debt_service_change_pct}")
