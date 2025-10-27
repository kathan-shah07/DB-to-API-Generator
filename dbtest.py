import time
import sqlite3
from urllib.parse import urlparse


def test_connection(sqlalchemy_url: str, timeout_seconds: float = 5.0) -> dict:
    """Lightweight connectivity check supporting sqlite URLs for now.

    Returns {ok: True, latency_ms: N} or {ok: False, error: str}.
    For non-sqlite URLs returns an error indicating unsupported scheme.
    """
    start = time.perf_counter()
    if not isinstance(sqlalchemy_url, str):
        return {"ok": False, "error": "invalid url"}

    parsed = urlparse(sqlalchemy_url)
    scheme = parsed.scheme
    try:
        if scheme == "sqlite":
            # support sqlite:///:memory: and sqlite:///relative/path.db
            if sqlalchemy_url.endswith(":memory:"):
                conn = sqlite3.connect(":memory:")
            else:
                # remove leading slashes from path
                path = sqlalchemy_url[len("sqlite:///"):]
                conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            conn.close()
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"ok": True, "latency_ms": latency_ms}
        else:
            return {"ok": False, "error": f"unsupported scheme: {scheme}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
