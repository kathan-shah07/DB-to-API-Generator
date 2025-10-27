import os
import json
from typing import List
from uuid import uuid4
from datetime import datetime, timezone

METADATA_DIR = os.environ.get("METADATA_DIR", os.path.join(os.path.dirname(__file__), "metadata"))
CONNECTORS_FILE = os.path.join(METADATA_DIR, "connectors.json")


def ensure_metadata_dir():
    os.makedirs(METADATA_DIR, exist_ok=True)


def read_connectors() -> List[dict]:
    if not os.path.exists(CONNECTORS_FILE):
        return []
    with open(CONNECTORS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def write_connectors_atomic(data: List[dict]):
    ensure_metadata_dir()
    tmp = CONNECTORS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CONNECTORS_FILE)


def add_connector_entry(name: str, sqlalchemy_url: str) -> str:
    if not sqlalchemy_url:
        raise ValueError("sqlalchemy_url is required")
    connectors = read_connectors()
    new_id = uuid4().hex
    entry = {
        "id": new_id,
        "name": name,
        "sqlalchemy_url": sqlalchemy_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    connectors.append(entry)
    write_connectors_atomic(connectors)
    return new_id


def get_connector_by_id(connector_id: str) -> dict | None:
    connectors = read_connectors()
    for c in connectors:
        if c.get("id") == connector_id:
            return c
    return None


def update_connector(connector_id: str, name: str | None = None, sqlalchemy_url: str | None = None) -> dict | None:
    """Update connector fields and write back atomically. Returns updated entry or None if not found."""
    connectors = read_connectors()
    changed = False
    for i, c in enumerate(connectors):
        if c.get("id") == connector_id:
            if name is not None:
                c["name"] = name
                changed = True
            if sqlalchemy_url is not None:
                c["sqlalchemy_url"] = sqlalchemy_url
                changed = True
            connectors[i] = c
            break
    else:
        return None

    if changed:
        write_connectors_atomic(connectors)
    return c


def delete_connector(connector_id: str) -> bool:
    """Delete connector by id. Also marks any mappings that reference this connector as invalid (if mappings.json exists).
    Returns True if a connector was deleted, False otherwise.
    """
    connectors = read_connectors()
    new_connectors = [c for c in connectors if c.get("id") != connector_id]
    if len(new_connectors) == len(connectors):
        return False

    write_connectors_atomic(new_connectors)

    # try to mark mappings invalid
    mappings_file = os.path.join(METADATA_DIR, "mappings.json")
    if os.path.exists(mappings_file):
        try:
            with open(mappings_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
        except Exception:
            mappings = []

        changed = False
        for m in mappings:
            if m.get("connector_id") == connector_id:
                m["connector_valid"] = False
                m["deployed"] = False
                changed = True

        if changed:
            tmp = mappings_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, mappings_file)

    return True


def write_schema_snapshot(connector_id: str, snapshot: dict) -> dict:
    """Append a new schema snapshot entry to schemas.json and return the saved record."""
    schemas_file = os.path.join(METADATA_DIR, "schemas.json")
    if os.path.exists(schemas_file):
        try:
            with open(schemas_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    else:
        data = []

    record = {
        "id": uuid4().hex,
        "connector_id": connector_id,
        "snapshot": snapshot,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data.append(record)

    tmp = schemas_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, schemas_file)

    return record


def read_schemas() -> list:
    schemas_file = os.path.join(METADATA_DIR, "schemas.json")
    if not os.path.exists(schemas_file):
        return []
    try:
        with open(schemas_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# --- queries storage ---
QUERIES_FILE = os.path.join(METADATA_DIR, "queries.json")


def read_queries() -> list:
    if not os.path.exists(QUERIES_FILE):
        return []
    try:
        with open(QUERIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_queries_atomic(data: list):
    ensure_metadata_dir()
    tmp = QUERIES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, QUERIES_FILE)


def add_query_entry(connector_id: str, name: str, sql_text: str, is_proc: bool = False, description: str | None = None) -> str:
    """Add a saved query entry. Validates connector exists and basic structure of sql_text for procs."""
    # ensure connector exists
    if not get_connector_by_id(connector_id):
        raise ValueError("connector_id not found")

    if not sql_text or not sql_text.strip():
        raise ValueError("sql_text is required")

    # basic validation for stored-proc flag
    if is_proc:
        low = sql_text.strip().lower()
        if not (low.startswith("call") or low.startswith("exec") or "procedure" in low):
            # allow creation but warn via error
            raise ValueError("is_proc=true but sql_text does not look like a stored procedure call")

    queries = read_queries()
    new_id = uuid4().hex
    entry = {
        "id": new_id,
        "connector_id": connector_id,
        "name": name,
        "sql_text": sql_text,
        "is_proc": bool(is_proc),
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    queries.append(entry)
    write_queries_atomic(queries)
    return new_id


# --- mappings storage ---
MAPPINGS_FILE = os.path.join(METADATA_DIR, "mappings.json")


def read_mappings() -> list:
    if not os.path.exists(MAPPINGS_FILE):
        return []
    try:
        with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_mappings_atomic(data: list):
    ensure_metadata_dir()
    tmp = MAPPINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, MAPPINGS_FILE)


def _validate_params_json(params_json) -> bool:
    # Expect a list of parameter definitions: {name, in, type, required?, default?}
    if not isinstance(params_json, list):
        return False
    valid_ins = {"path", "query", "body", "header"}
    valid_types = {"string", "integer", "number", "boolean"}
    for p in params_json:
        if not isinstance(p, dict):
            return False
        if "name" not in p or "in" not in p or "type" not in p:
            return False
        if p["in"] not in valid_ins:
            return False
        if p["type"] not in valid_types:
            return False
    return True


def add_mapping_entry(query_id: str, connector_id: str, path: str, method: str, params_json: list, auth_required: bool = True) -> str:
    """Add a mapping, validating uniqueness of path+method and params_json shape."""
    # basic checks
    if not path or not path.startswith("/"):
        raise ValueError("path must start with /")
    method_u = method.upper()
    if method_u not in {"GET", "POST", "PUT", "DELETE"}:
        raise ValueError("method must be one of GET/POST/PUT/DELETE")

    if not _validate_params_json(params_json):
        raise ValueError("params_json malformed")

    # ensure connector and query exist
    if not get_connector_by_id(connector_id):
        raise ValueError("connector_id not found")
    queries = read_queries()
    if not any(q.get("id") == query_id for q in queries):
        raise ValueError("query_id not found")

    mappings = read_mappings()
    # path uniqueness (path + method)
    for m in mappings:
        if m.get("path") == path and m.get("method") == method_u:
            raise ValueError("path already in use for this method")

    new_id = uuid4().hex
    entry = {
        "id": new_id,
        "query_id": query_id,
        "connector_id": connector_id,
        "path": path,
        "method": method_u,
        "params_json": params_json,
        "auth_required": bool(auth_required),
        "deployed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    mappings.append(entry)
    write_mappings_atomic(mappings)
    return new_id


def set_mapping_deployed(mapping_id: str, deployed: bool = True) -> dict | None:
    """Mark a mapping as deployed/undeployed and return the updated mapping."""
    mappings = read_mappings()
    for i, m in enumerate(mappings):
        if m.get("id") == mapping_id:
            m["deployed"] = bool(deployed)
            mappings[i] = m
            write_mappings_atomic(mappings)
            return m
    return None


def append_log(record: dict) -> None:
    """Append a small log record to logs.json."""
    logs_file = os.path.join(METADATA_DIR, "logs.json")
    if os.path.exists(logs_file):
        try:
            with open(logs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    else:
        data = []

    data.append(record)

    tmp = logs_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, logs_file)


def read_logs() -> list:
    """Read logs.json and return list of records."""
    logs_file = os.path.join(METADATA_DIR, "logs.json")
    if not os.path.exists(logs_file):
        return []
    try:
        with open(logs_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_deployed_mappings() -> list:
    """Return list of mappings that have deployed=True."""
    mappings = read_mappings()
    return [m for m in mappings if m.get("deployed")]


# --- api keys ---
API_KEYS_FILE = os.path.join(METADATA_DIR, "api_keys.json")


def read_api_keys() -> list:
    if not os.path.exists(API_KEYS_FILE):
        return []
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_api_keys_atomic(data: list):
    ensure_metadata_dir()
    tmp = API_KEYS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, API_KEYS_FILE)


def add_api_key_entry(role: str = "consumer") -> str:
    """Generate an API key (plaintext returned once) and store only its bcrypt hash.

    Returns the plaintext token.
    """
    import secrets
    import bcrypt

    if role not in ("admin", "consumer"):
        raise ValueError("role must be 'admin' or 'consumer'")

    token = secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    keys = read_api_keys()
    new_id = uuid4().hex
    entry = {"id": new_id, "role": role, "hash": hashed, "created_at": datetime.now(timezone.utc).isoformat()}
    keys.append(entry)
    write_api_keys_atomic(keys)
    return token


def validate_api_key(token: str) -> dict | None:
    """Return the api key record if token matches a stored hash, else None."""
    import bcrypt

    if not token:
        return None
    keys = read_api_keys()
    for k in keys:
        try:
            if bcrypt.checkpw(token.encode("utf-8"), k.get("hash").encode("utf-8")):
                return k
        except Exception:
            continue
    return None


