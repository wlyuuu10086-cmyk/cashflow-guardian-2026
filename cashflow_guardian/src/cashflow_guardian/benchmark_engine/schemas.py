from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class PeerGroupDefinition(BaseModel):
    method: str = Field(..., description="Method used to establish peer group: industry_and_revenue_band, industry_only, or industry_benchmark_table")
    industry: str
    revenue_band: Optional[str] = None
    peer_count: int

class BenchmarkMetricComparison(BaseModel):
    metric_name: str
    business_value: Optional[float] = None
    peer_value: Optional[float] = None
    absolute_gap: Optional[float] = None
    percentage_gap: Optional[float] = None
    percentile_rank: Optional[float] = None
    direction: str = Field(..., description="better, similar, worse, or unavailable")
    interpretation_code: str
    source_provenance: str = Field(..., description="observed_data or benchmark_table")

class BenchmarkProvenance(BaseModel):
    source_tables: List[str]
    as_of_month: str
    query_timestamp: str
    future_data_used: bool = False
    warnings: List[str] = Field(default_factory=list)

class BusinessBenchmarkResult(BaseModel):
    business_id: str
    as_of_month: str
    peer_group: PeerGroupDefinition
    metrics: Dict[str, BenchmarkMetricComparison]
    provenance: BenchmarkProvenance
    warnings: List[str] = Field(default_factory=list)
