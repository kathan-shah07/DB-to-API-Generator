import time
import sqlite3
from urllib.parse import urlparse


def test_connection(sqlalchemy_url: str, timeout_seconds: float = 5.0) -> dict:
    import time
    start = time.perf_counter()
    from sqlalchemy import create_engine, text
    try:
        # Use a very short timeout for connectivity check
        engine = create_engine(sqlalchemy_url, connect_args={'connect_timeout': int(timeout_seconds)})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"ok": True, "latency_ms": latency_ms}
    except Exception as e:
        # Some dialects don't support connect_timeout in connect_args
        try:
            engine = create_engine(sqlalchemy_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"ok": True, "latency_ms": latency_ms}
        except Exception as e2:
            return {"ok": False, "error": str(e2)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
