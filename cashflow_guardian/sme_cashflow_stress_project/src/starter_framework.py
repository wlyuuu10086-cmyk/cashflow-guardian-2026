from pathlib import Path
import duckdb
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "sme_cashflow_stress.duckdb"
con = duckdb.connect(str(DB_PATH))
print(con.sql("SHOW TABLES").df())
print(con.sql("SELECT * FROM vw_table_row_counts ORDER BY row_count DESC").df())
