import time
from typing import Dict


class RateLimiter:
    """Simple in-memory fixed-window rate limiter per key (mapping_id).

    Not distributed; suitable for unit tests and single-process server.
    """

    def __init__(self):
        # store: key -> {window_start, count, window_seconds, limit}
        self._store: Dict[str, Dict] = {}

    def configure(self, key: str, limit: int, window_seconds: int):
        self._store[key] = {"window_start": 0, "count": 0, "limit": limit, "window_seconds": window_seconds}

    def allow(self, key: str) -> bool:
        now = int(time.time())
        rec = self._store.get(key)
        if rec is None:
            # default allow unlimited
            return True
        ws = rec["window_start"]
        if now - ws >= rec["window_seconds"]:
            # reset window
            rec["window_start"] = now
            rec["count"] = 0
        if rec["count"] < rec["limit"]:
            rec["count"] += 1
            return True
        return False


_rl = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rl
