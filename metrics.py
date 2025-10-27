import time

_counters = {}


def incr(name: str, amount: int = 1):
    _counters[name] = _counters.get(name, 0) + amount


def get_counter(name: str) -> int:
    return _counters.get(name, 0)


def health_check() -> dict:
    return {"status": "ok", "time": time.time(), "metrics": dict(_counters)}
