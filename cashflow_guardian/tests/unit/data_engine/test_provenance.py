import pytest
from datetime import datetime
from cashflow_guardian.data_engine.provenance import build_provenance
from cashflow_guardian.data_engine.schemas import ProvenanceMetadata

def test_provenance_structure():
    """Tests the structure and fields of ProvenanceMetadata."""
    prov = build_provenance(
        source_tables=["business_monthly_snapshots"],
        as_of_month="2025-06",
        row_count=10,
        warnings=["Test warning"]
    )
    
    assert isinstance(prov, ProvenanceMetadata)
    assert prov.source_tables == ["business_monthly_snapshots"]
    assert prov.as_of_month == "2025-06"
    assert prov.row_count == 10
    assert prov.future_data_used is False
    assert prov.warnings == ["Test warning"]
    
    # Check timestamp format
    dt = datetime.strptime(prov.query_timestamp, "%Y-%m-%dT%H:%M:%SZ")
    assert isinstance(dt, datetime)
