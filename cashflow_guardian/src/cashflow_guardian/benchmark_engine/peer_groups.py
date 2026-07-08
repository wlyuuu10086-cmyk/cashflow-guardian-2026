from typing import List, Tuple, Optional
import duckdb

def determine_peer_group(
    business_id: str,
    as_of_month: str,
    conn: duckdb.DuckDBPyConnection,
    min_peer_count: int = 5
) -> Tuple[str, str, Optional[str], List[str]]:
    """Identifies the peer group for a business as of a target month.
    
    Excludes the target business from the peer IDs.
    Returns:
        Tuple of (method, industry, revenue_band, peer_ids)
    """
    # 1. Fetch business details
    row = conn.execute(
        "SELECT industry, revenue_band FROM business_customers WHERE business_id = ?",
        (business_id,)
    ).fetchone()
    
    if not row:
        raise ValueError(f"Business ID {business_id} was not found in the database.")
        
    industry, revenue_band = row
    
    # 2. Try Preferred Peer Group: Same Industry + Same Revenue Band as of target month
    pref_peers = conn.execute(
        """
        SELECT DISTINCT c.business_id
        FROM business_customers c
        JOIN business_monthly_snapshots s ON c.business_id = s.business_id
        WHERE c.industry = ? AND c.revenue_band = ? AND s.month = ? AND c.business_id != ?
        """,
        (industry, revenue_band, as_of_month, business_id)
    ).fetchall()
    
    pref_peer_ids = [r[0] for r in pref_peers]
    if len(pref_peer_ids) >= min_peer_count:
        return "industry_and_revenue_band", industry, revenue_band, pref_peer_ids
        
    # 3. Try Fallback: Same Industry as of target month
    fallback_peers = conn.execute(
        """
        SELECT DISTINCT c.business_id
        FROM business_customers c
        JOIN business_monthly_snapshots s ON c.business_id = s.business_id
        WHERE c.industry = ? AND s.month = ? AND c.business_id != ?
        """,
        (industry, as_of_month, business_id)
    ).fetchall()
    
    fallback_peer_ids = [r[0] for r in fallback_peers]
    if len(fallback_peer_ids) >= min_peer_count:
        return "industry_only", industry, None, fallback_peer_ids
        
    # 4. Final Fallback: Industry Benchmark Table
    return "industry_benchmark_table", industry, None, []
