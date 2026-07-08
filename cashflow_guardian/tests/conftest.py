import pytest
import duckdb
from pathlib import Path
from cashflow_guardian.data_engine.connection import get_repo_root

@pytest.fixture(scope="session")
def real_db_path() -> Path:
    """Returns the absolute path to the real DuckDB database."""
    return get_repo_root() / "sme_cashflow_stress_project" / "data" / "sme_cashflow_stress.duckdb"

class ConnectionWrapper:
    """Wrapper around duckdb connection to prevent tests from closing the shared database."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)
    def close(self):
        # Ignore close calls to keep the shared in-memory DB alive
        pass
    def fetchall(self):
        return self._conn.fetchall()
    def fetchone(self):
        return self._conn.fetchone()
    def __getattr__(self, name):
        return getattr(self._conn, name)

@pytest.fixture
def mock_db_conn():
    """Provides an in-memory DuckDB database connection loaded with minimal mock schemas and data."""
    conn = duckdb.connect(":memory:")
    
    # 1. Create business_customers
    conn.execute(
        """
        CREATE TABLE business_customers (
            business_id VARCHAR,
            business_name VARCHAR,
            industry_id VARCHAR,
            industry VARCHAR,
            region_id VARCHAR,
            region VARCHAR,
            state VARCHAR,
            city_tier VARCHAR,
            years_in_business INTEGER,
            revenue_band VARCHAR,
            estimated_monthly_revenue_band_midpoint INTEGER,
            employee_count_base INTEGER,
            legal_structure VARCHAR,
            credit_score_band_at_origination VARCHAR,
            has_prior_delinquency INTEGER,
            owner_experience_years INTEGER,
            online_sales_share DOUBLE,
            relationship_manager_id VARCHAR,
            onboarding_date DATE,
            primary_bank_account_type VARCHAR
        )
        """
    )
    
    # Insert mock business customers with full metadata
    conn.execute(
        """
        INSERT INTO business_customers (
            business_id, business_name, industry_id, industry, region, 
            revenue_band, relationship_manager_id
        ) VALUES
        ('B00001', 'Test Corp', 'IND_01', 'Wholesale Trade', 'Northeast', '1M-5M', 'RM_01'),
        ('B00002', 'Beta LLC', 'IND_02', 'Retail Trade', 'West', '500k-1M', 'RM_02')
        """
    )
    
    # 2. Create business_monthly_snapshots
    conn.execute(
        """
        CREATE TABLE business_monthly_snapshots (
            business_id VARCHAR,
            month VARCHAR,
            month_start_date DATE,
            opening_cash_balance_proxy DOUBLE,
            ending_cash_balance_proxy DOUBLE,
            avg_daily_balance_proxy DOUBLE,
            overdraft_days_proxy INTEGER,
            transaction_count BIGINT,
            cash_inflow_observed DOUBLE,
            cash_outflow_observed DOUBLE,
            net_cash_flow_observed DOUBLE,
            invoice_count BIGINT,
            invoice_amount_total DOUBLE,
            avg_days_to_pay DOUBLE,
            late_invoice_rate DOUBLE,
            payroll_amount DOUBLE,
            employee_count INTEGER,
            scheduled_debt_service DOUBLE,
            actual_debt_service DOUBLE,
            max_dpd INTEGER,
            available_credit_drawn_ratio DOUBLE
        )
        """
    )
    
    # Insert 6 months of snapshots for B00001 and 2 months of snapshots for B00002 (to test insufficient history)
    months = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
    for i, m in enumerate(months):
        conn.execute(
            """
            INSERT INTO business_monthly_snapshots VALUES
            (?, ?, '2025-01-01', 50000.0, 52000.0 + ?, 51000.0, 0, 42, 10000.0, 8000.0, 2000.0, 10, 5000.0, 10.0, 0.05, 3000.0, 5, 1000.0, 1000.0, 0, 0.25)
            """,
            ("B00001", m, i * 500.0)
        )
        
    # Insert 2 months for B00002
    for m in ["2025-05", "2025-06"]:
        conn.execute(
            """
            INSERT INTO business_monthly_snapshots VALUES
            (?, ?, '2025-05-01', 10000.0, 9000.0, 9500.0, 3, 15, 2000.0, 3000.0, -1000.0, 5, 2000.0, 25.0, 0.40, 1500.0, 2, 0.0, 0.0, 0, 0.0)
            """,
            ("B00002", m)
        )
        
    # 3. Create industry_benchmark
    conn.execute(
        """
        CREATE TABLE industry_benchmark (
            industry_id VARCHAR,
            industry VARCHAR,
            benchmark_margin DECIMAL(3,2),
            benchmark_cash_flow_volatility DECIMAL(3,2),
            benchmark_collection_days INTEGER,
            benchmark_repayment_burden_pct INTEGER,
            payroll_intensity DECIMAL(3,2),
            seasonality_peak_month INTEGER,
            typical_transaction_intensity DECIMAL(2,1),
            economic_sensitivity DECIMAL(3,2)
        )
        """
    )
    
    conn.execute(
        """
        INSERT INTO industry_benchmark VALUES
        ('IND_01', 'Wholesale Trade', 0.15, 0.20, 12, 10, 0.12, 11, 2.5, 0.8),
        ('IND_02', 'Retail Trade', 0.08, 0.35, 5, 5, 0.25, 12, 5.0, 1.2)
        """
    )
    
    # 4. Create expected tables config (expected by health check)
    conn.execute("CREATE VIEW vw_table_row_counts AS SELECT 'business_customers' AS table_name, 2 AS row_count")
    
    wrapped = ConnectionWrapper(conn)
    yield wrapped
    
    # Actually close it when the fixture is torn down
    conn.close()
