from datetime import datetime
from typing import List, Optional
from .schemas import ProvenanceMetadata

def build_provenance(
    source_tables: List[str],
    as_of_month: str,
    row_count: int,
    warnings: Optional[List[str]] = None
) -> ProvenanceMetadata:
    """Constructs a ProvenanceMetadata instance.
    
    Guarantees that future_data_used is always False.
    """
    warns = list(warnings) if warnings is not None else []
    
    # query_timestamp is formatted as ISO-8601 UTC
    timestamp_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return ProvenanceMetadata(
        source_tables=source_tables,
        as_of_month=as_of_month,
        query_timestamp=timestamp_str,
        row_count=row_count,
        future_data_used=False,
        warnings=warns
    )
