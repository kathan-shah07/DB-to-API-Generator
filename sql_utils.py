import re


_param_pattern = re.compile(r"[:@]([a-zA-Z_][a-zA-Z0-9_]*)")


def extract_named_params(sql: str) -> set:
    """Return set of named parameters used in SQL text (simple regex-based)."""
    return set(_param_pattern.findall(sql or ""))


def validate_params_against_sql(sql: str, params: dict) -> tuple[bool, str]:
    """Validate that provided params cover those used in SQL. Returns (ok, message)."""
    used = extract_named_params(sql)
    missing = [p for p in used if p not in params]
    if missing:
        return False, f"missing params: {missing}"
    return True, "ok"
