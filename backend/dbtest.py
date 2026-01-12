import time
from db_adapter import DatabaseClient

def test_connection(sqlalchemy_url: str, timeout_seconds: float = 5.0) -> dict:
    """Check connectivity using the DatabaseClient."""
    start = time.perf_counter()
    try:
        # Try to fetch 1 row of a dummy query
        client = DatabaseClient(sqlalchemy_url)
        client.fetch_all("SELECT 1")
        latency_ms = int((time.perf_counter() - start) * 1000)
        client.dispose()
        return {"ok": True, "latency_ms": latency_ms}
    except Exception as e:
        return {"ok": False, "error": str(e)}
