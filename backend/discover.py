from typing import Dict, List, Any
from db_adapter import DatabaseClient

def discover_schema(sqlalchemy_url: str, sample_rows: int = 5) -> Dict:
    """Discover schema for the given URL.
    Rule 3: No direct cursor usage.
    """
    snapshot = {"tables": {}}
    client = DatabaseClient(sqlalchemy_url)
    try:
        inspector = client.get_inspector()
        for table_name in inspector.get_table_names():
            cols = []
            for col in inspector.get_columns(table_name):
                cols.append({
                    "name": col.get("name"),
                    "type": str(col.get("type")),
                    "nullable": col.get("nullable"),
                    "default": col.get("default"),
                })

            pk = inspector.get_pk_constraint(table_name).get("constrained_columns", [])

            # Sample rows
            sample = []
            try:
                # Use fetch_all for standardized row shape
                # We need to quote table names for safety
                query = f"SELECT * FROM \"{table_name}\" LIMIT {sample_rows}"
                # For SQLite, double quotes might not be enough if it's not strictly followed, 
                # but SQLAlchemy usually handles it.
                rows = client.fetch_all(query)
                for r in rows:
                    # Convert dict to list of values for the sample_rows format expected by frontend
                    sample.append([None if x is None else (x if isinstance(x, (int, float, bool)) else str(x)) for x in r.values()])
            except Exception:
                sample = []

            snapshot["tables"][table_name] = {"columns": cols, "pk": pk, "sample_rows": sample}

        return snapshot
    finally:
        client.dispose()

def get_table_info(sqlalchemy_url: str, table: str, sample_rows: int = 5) -> Dict:
    """Return column metadata, primary key and sample rows for a single table."""
    client = DatabaseClient(sqlalchemy_url)
    try:
        inspector = client.get_inspector()
        cols = []
        for col in inspector.get_columns(table):
            cols.append({
                "name": col.get("name"),
                "type": str(col.get("type")),
                "nullable": col.get("nullable"),
                "default": col.get("default"),
            })

        pk = inspector.get_pk_constraint(table).get("constrained_columns", [])

        sample = []
        try:
            query = f"SELECT * FROM \"{table}\" LIMIT {sample_rows}"
            rows = client.fetch_all(query)
            for r in rows:
                sample.append([None if x is None else (x if isinstance(x, (int, float, bool)) else str(x)) for x in r.values()])
        except Exception:
            sample = []

        return {"table": table, "columns": cols, "pk": pk, "sample_rows": sample}
    finally:
        client.dispose()
