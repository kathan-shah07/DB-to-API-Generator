from urllib.parse import urlparse
import sqlite3
from typing import Dict


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite://")


def _sqlite_path(url: str) -> str:
    if url.endswith(":memory:"):
        return ":memory:"
    return url[len("sqlite:///"):]


def discover_schema(sqlalchemy_url: str, sample_rows: int = 5) -> Dict:
    """Discover schema for the given URL.

    Returns a snapshot dict: {tables: {table_name: {columns: [...], pk: [...], sample_rows: [...]}}}
    """
    snapshot = {"tables": {}}

    if _is_sqlite_url(sqlalchemy_url):
        path = _sqlite_path(sqlalchemy_url)
        conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            # columns
            cur.execute(f"PRAGMA table_info('{table}')")
            cols = []
            rows = cur.fetchall()
            for col in rows:
                cols.append({
                    "name": col[1],
                    "type": col[2],
                    "nullable": not bool(col[3]),
                    "default": col[4],
                })

            pk = [r[1] for r in rows if r[5]]

            sample = []
            try:
                cur.execute(f"SELECT * FROM '{table}' LIMIT ?", (sample_rows,))
                for r in cur.fetchall():
                    sample.append([None if x is None else (x if isinstance(x, (int, float, bool)) else str(x)) for x in r])
            except Exception:
                sample = []

            snapshot["tables"][table] = {"columns": cols, "pk": pk, "sample_rows": sample}

        conn.close()
        return snapshot

    # non-sqlite: try to import SQLAlchemy lazily
    try:
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.exc import SQLAlchemyError
    except Exception as e:
        raise RuntimeError("SQLAlchemy not available or failed to import; install SQLAlchemy to discover non-sqlite databases") from e

    engine = create_engine(sqlalchemy_url)
    inspector = inspect(engine)
    try:
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

            sample = []
            with engine.connect() as conn:
                try:
                    res = conn.execute(text(f"SELECT * FROM \"{table_name}\" LIMIT :limit"), {"limit": sample_rows})
                    rows = res.fetchall()
                    for r in rows:
                        sample.append([None if x is None else (str(x) if not isinstance(x, (int, float, bool)) else x) for x in r])
                except Exception:
                    sample = []

            snapshot["tables"][table_name] = {"columns": cols, "pk": pk, "sample_rows": sample}

        return snapshot
    except SQLAlchemyError:
        raise
    finally:
        engine.dispose()


def get_table_info(sqlalchemy_url: str, table: str, sample_rows: int = 5) -> Dict:
    """Return column metadata, primary key and sample rows for a single table.

    Works for sqlite without SQLAlchemy and for other DBs via SQLAlchemy inspector.
    """
    if _is_sqlite_url(sqlalchemy_url):
        path = _sqlite_path(sqlalchemy_url)
        conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
        cur = conn.cursor()

        cur.execute(f"PRAGMA table_info('{table}')")
        rows = cur.fetchall()
        cols = []
        for col in rows:
            cols.append({
                "name": col[1],
                "type": col[2],
                "nullable": not bool(col[3]),
                "default": col[4],
            })

        pk = [r[1] for r in rows if r[5]]

        sample = []
        try:
            cur.execute(f"SELECT * FROM '{table}' LIMIT ?", (sample_rows,))
            for r in cur.fetchall():
                sample.append([None if x is None else (x if isinstance(x, (int, float, bool)) else str(x)) for x in r])
        except Exception:
            sample = []

        conn.close()
        return {"table": table, "columns": cols, "pk": pk, "sample_rows": sample}

    # non-sqlite: lazy import SQLAlchemy
    try:
        from sqlalchemy import create_engine, inspect, text
    except Exception as e:
        raise RuntimeError("SQLAlchemy required for non-sqlite table inspection") from e

    engine = create_engine(sqlalchemy_url)
    inspector = inspect(engine)
    try:
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
        with engine.connect() as conn:
            try:
                res = conn.execute(text(f"SELECT * FROM \"{table}\" LIMIT :limit"), {"limit": sample_rows})
                rows = res.fetchall()
                for r in rows:
                    sample.append([None if x is None else (str(x) if not isinstance(x, (int, float, bool)) else x) for x in r])
            except Exception:
                sample = []

        return {"table": table, "columns": cols, "pk": pk, "sample_rows": sample}
    finally:
        engine.dispose()
