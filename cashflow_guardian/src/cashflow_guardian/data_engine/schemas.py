from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, constr

# Pattern definitions for Business ID and As of Month
BusinessIdentifier = constr(pattern=r"^(B\d{5}|BUS_\d{3,4})$")
AsOfMonth = constr(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")

class ProvenanceMetadata(BaseModel):
    source_tables: List[str] = Field(..., description="List of physical tables queried.")
    as_of_month: str = Field(..., description="The query time-boundary month.")
    query_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    row_count: int = Field(..., ge=0)
    future_data_used: bool = Field(default=False)
    warnings: List[str] = Field(default_factory=list)

class DatabaseHealthResult(BaseModel):
    database_available: bool
    read_only: bool
    required_tables_present: bool
    missing_tables: List[str]
    row_counts: Dict[str, int]
    warnings: List[str]
    database_size_bytes: int = 0

class DataQualityResult(BaseModel):
    status: str = Field(..., description="Verification status: COMPLETED, WARNING, or BLOCKED")
    can_build_features: bool
    missing_fields: List[str]
    missing_months: List[str]
    transaction_gaps: bool
    has_sufficient_history: bool
    errors: List[str]
    warnings: List[str]
    provenance: Optional[ProvenanceMetadata] = None

class BusinessMonthlyMetric(BaseModel):
    month: str
    cash_inflow: float
    cash_outflow: float
    net_cash_flow: float
    ending_balance: float
    average_daily_balance: float
    overdraft_days: int
    invoice_count: int
    average_days_to_pay: float
    late_invoice_rate: float
    payroll_amount: float
    employee_count: int
    scheduled_debt_service: float
    actual_debt_service: float
    maximum_days_past_due: int
    credit_utilization_ratio: float

class BusinessHistoryResult(BaseModel):
    business_id: str
    history_months: int
    snapshots: List[BusinessMonthlyMetric]
    provenance: ProvenanceMetadata

class PortfolioBusinessRecord(BaseModel):
    business_id: str
    business_name: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None
    revenue_band: Optional[str] = None
    relationship_manager_id: Optional[str] = None
    cash_inflow: float
    cash_outflow: float
    net_cash_flow: float
    ending_cash_balance: float
    average_collection_days: float
    late_invoice_rate: float
    payroll_amount: float
    scheduled_debt_service: float
    maximum_days_past_due: int
    credit_utilization_ratio: float
    data_quality_status: str

class PortfolioSnapshotResult(BaseModel):
    as_of_month: str
    records: List[PortfolioBusinessRecord]
    provenance: ProvenanceMetadata

class PeerBenchmarkResult(BaseModel):
    business_id: str
    industry: str
    peer_metrics: Dict[str, float]
    business_metrics: Dict[str, float]
    deviations: Dict[str, float]
    provenance: ProvenanceMetadata

class FeatureVectorResult(BaseModel):
    business_id: str
    month: str
    features: Dict[str, Any]
    feature_names: List[str]
    missing_feature_warnings: List[str]
    provenance: ProvenanceMetadata
    future_data_used: bool = False
