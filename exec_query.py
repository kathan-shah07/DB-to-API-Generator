from urllib.parse import urlparse
import sqlite3
from typing import Any, Dict


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite://")


def _sqlite_path(url: str) -> str:
    if url.endswith(":memory:"):
        return ":memory:"
    return url[len("sqlite:///"):]


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


def preview_query(connector: Dict, sql_text: str, params: Dict[str, Any] | None = None, max_rows: int = 10) -> Dict:
    """Execute the SQL in a read-only/transaction-rolled-back mode and return sample results.

    Returns: {ok: True, rows: [dict], columns: [name,...]} or {ok: False, error: str}
    """
    if params is None:
        params = {}

    url = connector.get("sqlalchemy_url") if isinstance(connector, dict) else connector
    if not url:
        return {"ok": False, "error": "missing connector url"}

    if _is_sqlite_url(url):
        path = _sqlite_path(url)
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            # begin transaction
            cur.execute("BEGIN")
            try:
                # execute
                cur.execute(sql_text, params)
                if sql_text.strip().lower().startswith("select"):
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchmany(max_rows)
                    result_rows = []
                    for r in rows:
                        result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                    # rollback to avoid side-effects
                    conn.rollback()
                    return {"ok": True, "rows": result_rows, "columns": cols}
                else:
                    # non-select: provide rowcount and rollback
                    rowcount = cur.rowcount
                    conn.rollback()
                    return {"ok": True, "message": f"executed, rowcount={rowcount}"}
            except Exception as e:
                conn.rollback()
                return {"ok": False, "error": str(e)}
        finally:
            conn.close()

    # non-sqlite: try to use SQLAlchemy
    try:
        from sqlalchemy import create_engine, text
    except Exception:
        return {"ok": False, "error": "SQLAlchemy is required for non-sqlite connectors"}

    engine = create_engine(url)
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            res = conn.execute(text(sql_text), params)
            if res.returns_rows:
                rows = res.fetchmany(max_rows)
                cols = res.keys()
                result_rows = []
                for r in rows:
                    result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                trans.rollback()
                engine.dispose()
                return {"ok": True, "rows": result_rows, "columns": list(cols)}
            else:
                rowcount = res.rowcount
                trans.rollback()
                engine.dispose()
                return {"ok": True, "message": f"executed, rowcount={rowcount}"}
        except Exception as e:
            try:
                trans.rollback()
            except Exception:
                pass
            engine.dispose()
            return {"ok": False, "error": str(e)}


def run_query(connector: Dict, sql_text: str, params: Dict[str, Any] | None = None, max_rows: int = 100, is_proc: bool = False) -> Dict:
    """Execute the SQL and return results. This is used by deployed runtime routes.

    Returns {ok: True, rows: [dict], columns: [..]} or {ok: False, error: str}
    """
    if params is None:
        params = {}

    url = connector.get("sqlalchemy_url") if isinstance(connector, dict) else connector
    if not url:
        return {"ok": False, "error": "missing connector url"}

    if _is_sqlite_url(url):
        path = _sqlite_path(url)
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            try:
                cur.execute(sql_text, params)
                if sql_text.strip().lower().startswith("select"):
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchmany(max_rows)
                    result_rows = []
                    for r in rows:
                        result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                    # indicate if there may be more rows available
                    return {"ok": True, "rows": result_rows, "columns": cols, "more": len(result_rows) >= max_rows}
                else:
                    rowcount = cur.rowcount
                    conn.commit()
                    return {"ok": True, "message": f"executed, rowcount={rowcount}", "rowcount": rowcount}
            except Exception as e:
                conn.rollback()
                return {"ok": False, "error": str(e)}
        finally:
            conn.close()

    # non-sqlite: use SQLAlchemy
    try:
        from sqlalchemy import create_engine, text
    except Exception:
        return {"ok": False, "error": "SQLAlchemy is required for non-sqlite connectors"}

    engine = create_engine(url)
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            res = conn.execute(text(sql_text), params)
            if res.returns_rows:
                rows = res.fetchmany(max_rows)
                cols = res.keys()
                result_rows = []
                for r in rows:
                    result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                trans.commit()
                engine.dispose()
                return {"ok": True, "rows": result_rows, "columns": list(cols), "more": len(result_rows) >= max_rows}
            else:
                rowcount = res.rowcount
                trans.commit()
                engine.dispose()
                return {"ok": True, "message": f"executed, rowcount={rowcount}", "rowcount": rowcount}
        except Exception as e:
            try:
                trans.rollback()
            except Exception:
                pass
            engine.dispose()
            return {"ok": False, "error": str(e)}
from urllib.parse import urlparse
import sqlite3
from typing import Any, Dict


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite://")


def _sqlite_path(url: str) -> str:
    if url.endswith(":memory:"):
        return ":memory:"
    return url[len("sqlite:///"):]


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


def preview_query(connector: Dict, sql_text: str, params: Dict[str, Any] | None = None, max_rows: int = 10) -> Dict:
    """Execute the SQL in a read-only/transaction-rolled-back mode and return sample results.

    Returns: {ok: True, rows: [dict], columns: [name,...]} or {ok: False, error: str}
    """
    if params is None:
        params = {}

    url = connector.get("sqlalchemy_url") if isinstance(connector, dict) else connector
    if not url:
        return {"ok": False, "error": "missing connector url"}

    if _is_sqlite_url(url):
        path = _sqlite_path(url)
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            # begin transaction
            cur.execute("BEGIN")
            try:
                # execute
                cur.execute(sql_text, params)
                if sql_text.strip().lower().startswith("select"):
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchmany(max_rows)
                    result_rows = []
                    for r in rows:
                        result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                    # rollback to avoid side-effects
                    conn.rollback()
                    return {"ok": True, "rows": result_rows, "columns": cols}
                else:
                    # non-select: provide rowcount and rollback
                    rowcount = cur.rowcount
                    conn.rollback()
                    return {"ok": True, "message": f"executed, rowcount={rowcount}"}
            except Exception as e:
                conn.rollback()
                return {"ok": False, "error": str(e)}
        finally:
            conn.close()

    # non-sqlite: try to use SQLAlchemy
    try:
        from sqlalchemy import create_engine, text
    except Exception:
        return {"ok": False, "error": "SQLAlchemy is required for non-sqlite connectors"}

    engine = create_engine(url)
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            res = conn.execute(text(sql_text), params)
            if res.returns_rows:
                rows = res.fetchmany(max_rows)
                cols = res.keys()
                result_rows = []
                for r in rows:
                    result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                trans.rollback()
                engine.dispose()
                return {"ok": True, "rows": result_rows, "columns": list(cols)}
            else:
                rowcount = res.rowcount
                trans.rollback()
                engine.dispose()
                return {"ok": True, "message": f"executed, rowcount={rowcount}"}
        except Exception as e:
            try:
                trans.rollback()
            except Exception:
                pass
            engine.dispose()
            return {"ok": False, "error": str(e)}


    def run_query(connector: Dict, sql_text: str, params: Dict[str, Any] | None = None, max_rows: int = 100) -> Dict:
        """Execute the SQL and return results. This is used by deployed runtime routes.

        Returns {ok: True, rows: [dict], columns: [..]} or {ok: False, error: str}
        """
        if params is None:
            params = {}

        url = connector.get("sqlalchemy_url") if isinstance(connector, dict) else connector
        if not url:
            return {"ok": False, "error": "missing connector url"}

        if _is_sqlite_url(url):
            path = _sqlite_path(url)
            conn = sqlite3.connect(path)
            try:
                cur = conn.cursor()
                try:
                    cur.execute(sql_text, params)
                    if sql_text.strip().lower().startswith("select"):
                        cols = [d[0] for d in cur.description] if cur.description else []
                        rows = cur.fetchmany(max_rows)
                        result_rows = []
                        for r in rows:
                            result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                        return {"ok": True, "rows": result_rows, "columns": cols}
                    else:
                        rowcount = cur.rowcount
                        conn.commit()
                        return {"ok": True, "message": f"executed, rowcount={rowcount}"}
                except Exception as e:
                    conn.rollback()
                    return {"ok": False, "error": str(e)}
            finally:
                conn.close()

        # non-sqlite: use SQLAlchemy
        try:
            from sqlalchemy import create_engine, text
        except Exception:
            return {"ok": False, "error": "SQLAlchemy is required for non-sqlite connectors"}

        engine = create_engine(url)
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                res = conn.execute(text(sql_text), params)
                if res.returns_rows:
                    rows = res.fetchmany(max_rows)
                    cols = res.keys()
                    result_rows = []
                    for r in rows:
                        result_rows.append({cols[i]: _to_json_safe(r[i]) for i in range(len(cols))})
                    trans.commit()
                    engine.dispose()
                    return {"ok": True, "rows": result_rows, "columns": list(cols)}
                else:
                    rowcount = res.rowcount
                    trans.commit()
                    engine.dispose()
                    return {"ok": True, "message": f"executed, rowcount={rowcount}"}
            except Exception as e:
                try:
                    trans.rollback()
                except Exception:
                    pass
                engine.dispose()
                return {"ok": False, "error": str(e)}
