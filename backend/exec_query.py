from typing import Any, Dict, List
from sqlalchemy import text
from db_adapter import DatabaseClient

def _to_json_safe(val: Any):
    # minimal conversion
    if val is None:
        return None
    if isinstance(val, (int, float, bool)):
        return val
    try:
        return str(val)
    except Exception:
        return None

def _get_url(connector: Dict | str) -> str:
    if isinstance(connector, dict):
        return connector.get("sqlalchemy_url", "")
    return connector

def preview_query(connector: Dict, sql_text: str, params: Dict[str, Any] | None = None, max_rows: int = 10) -> Dict:
    """Execute the SQL and return sample results. 
    Rule 3: No direct cursor usage here.
    """
    url = _get_url(connector)
    if not url:
        return {"ok": False, "error": "missing connector url"}

    client = DatabaseClient(url)
    try:
        # For preview, we still want to ensure we don't commit anything if the user provides a write query
        # Although DatabaseClient uses autocommit for SELECTs, we can wrap in a transaction if needed.
        # But SELECTs are safe. If it's a non-select, we don't want to commit in preview.
        
        if sql_text.strip().lower().startswith("select"):
            rows = client.fetch_all(sql_text, params)
            # Limit rows for preview
            rows = rows[:max_rows]
            
            # Apply json safety
            safe_rows = []
            for r in rows:
                safe_rows.append({k: _to_json_safe(v) for k, v in r.items()})
            
            cols = list(safe_rows[0].keys()) if safe_rows else []
            return {"ok": True, "rows": safe_rows, "columns": cols}
        else:
            # For non-select in preview, we use a custom block to rollback
            with client.engine.connect() as conn:
                with conn.begin() as trans:
                    res = conn.execute(text(sql_text), params or {})
                    rowcount = res.rowcount
                    trans.rollback()
            return {"ok": True, "message": f"preview: would execute, rowcount={rowcount}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        client.dispose()

def run_query(connector: Dict, sql_text: str, params: Dict[str, Any] | None = None, max_rows: int = 100, is_proc: bool = False) -> Dict:
    """Execute the SQL and return results. Used by runtime routes.
    Rule 3: Ban direct cursor usage.
    """
    url = _get_url(connector)
    if not url:
        return {"ok": False, "error": "missing connector url"}

    client = DatabaseClient(url)
    try:
        if sql_text.strip().lower().startswith("select"):
            rows = client.fetch_all(sql_text, params)
            # Handle max_rows limit
            more = len(rows) > max_rows
            rows = rows[:max_rows]
            
            safe_rows = []
            for r in rows:
                safe_rows.append({k: _to_json_safe(v) for k, v in r.items()})
            
            cols = list(safe_rows[0].keys()) if safe_rows else []
            return {"ok": True, "rows": safe_rows, "columns": cols, "more": more}
        else:
            rowcount = client.execute(sql_text, params)
            return {"ok": True, "message": f"executed, rowcount={rowcount}", "rowcount": rowcount}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        client.dispose()
