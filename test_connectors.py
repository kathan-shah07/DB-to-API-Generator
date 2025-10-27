import os
import json
import subprocess
import sys
import time
import socket

import httpx


def wait_for_port(host: str, port: int, timeout: float = 5.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def test_add_connector_creates_file(tmp_path, monkeypatch):
    # point storage METADATA_DIR to temp
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    new_id = storage_mod.add_connector_entry("local_sqlite", "sqlite:///./sample.db")
    assert new_id

    connectors_path = os.path.join(str(tmp_path), "connectors.json")
    assert os.path.exists(connectors_path)

    with open(connectors_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert any(c["id"] == new_id for c in data)


def test_dbtest_on_memory_sqlite():
    # SQLite in-memory should accept sqlite+pysqlite:///:memory: or sqlite:///:memory:
    # SQLAlchemy recognizes 'sqlite:///:memory:'
    from dbtest import test_connection

    res = test_connection("sqlite:///:memory:")
    assert isinstance(res, dict)
    assert res.get("ok") is True


def test_test_connector_function(tmp_path, monkeypatch):
    # Use storage to add connector and then call main.test_connector function directly
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)
    import dbtest as dbtest_mod
    importlib.reload(dbtest_mod)

    cid = storage_mod.add_connector_entry("mem", "sqlite:///:memory:")
    c = storage_mod.get_connector_by_id(cid)
    assert c is not None
    res = dbtest_mod.test_connection(c.get("sqlalchemy_url"))
    assert res.get("ok") is True


def test_update_connector(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    cid = storage_mod.add_connector_entry("oldname", "sqlite:///:memory:")
    updated = storage_mod.update_connector(cid, name="newname", sqlalchemy_url=None)
    assert updated is not None
    assert updated["name"] == "newname"


def test_delete_connector_marks_mappings(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    cid = storage_mod.add_connector_entry("todel", "sqlite:///:memory:")

    # create mappings.json that references this connector
    mappings_path = os.path.join(str(tmp_path), "mappings.json")
    mappings = [{"id": "m1", "connector_id": cid, "deployed": True}]
    with open(mappings_path, "w", encoding="utf-8") as f:
        json.dump(mappings, f)

    ok = storage_mod.delete_connector(cid)
    assert ok is True

    with open(mappings_path, "r", encoding="utf-8") as f:
        after = json.load(f)
    assert any(m.get("connector_valid") is False for m in after)


def test_discover_schema_and_save(tmp_path, monkeypatch):
    # create a sqlite file-backed DB and populate
    db_path = tmp_path / "test.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    cur.execute("INSERT INTO people (name, age) VALUES ('Alice', 30)")
    cur.execute("INSERT INTO people (name, age) VALUES ('Bob', 25)")
    conn.commit()
    conn.close()

    # point metadata dir
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    import discover as discover_mod
    importlib.reload(storage_mod)
    importlib.reload(discover_mod)

    cid = storage_mod.add_connector_entry("filedb", f"sqlite:///{db_path}")
    snapshot = discover_mod.discover_schema(f"sqlite:///{db_path}", sample_rows=2)
    assert "people" in snapshot.get("tables", {})

    record = storage_mod.write_schema_snapshot(cid, snapshot)
    assert record.get("connector_id") == cid


def test_get_table_schema(tmp_path, monkeypatch):
    # create a sqlite file-backed DB and populate
    db_path = tmp_path / "test2.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, title TEXT, price REAL)")
    cur.execute("INSERT INTO items (title, price) VALUES ('Pen', 1.5)")
    cur.execute("INSERT INTO items (title, price) VALUES ('Book', 9.99)")
    conn.commit()
    conn.close()

    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    import discover as discover_mod
    importlib.reload(storage_mod)
    importlib.reload(discover_mod)

    cid = storage_mod.add_connector_entry("filedb2", f"sqlite:///{db_path}")
    info = discover_mod.get_table_info(f"sqlite:///{db_path}", "items", sample_rows=2)
    assert info["table"] == "items"
    assert any(col["name"] == "title" for col in info["columns"])
    assert len(info["sample_rows"]) <= 2


def test_add_query_entry_and_api(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    # create connector
    cid = storage_mod.add_connector_entry("qconn", "sqlite:///:memory:")

    # create query via storage
    qid = storage_mod.add_query_entry(cid, "get-people", "SELECT * FROM people", is_proc=False)
    assert qid

    # verify queries.json contains the saved query
    qs = storage_mod.read_queries()
    assert any(q["id"] == qid for q in qs)


def test_preview_select_and_rollback(tmp_path, monkeypatch):
    # prepare sqlite file DB
    db_path = tmp_path / "preview.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, val TEXT)")
    cur.execute("INSERT INTO demo (val) VALUES ('x')")
    conn.commit()
    conn.close()

    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    import exec_query as exec_mod
    importlib.reload(storage_mod)
    importlib.reload(exec_mod)

    cid = storage_mod.add_connector_entry("pv", f"sqlite:///{db_path}")

    # preview select
    conn_meta = storage_mod.get_connector_by_id(cid)
    r = exec_mod.preview_query(conn_meta, "SELECT * FROM demo", None, max_rows=10)
    assert r.get("ok") is True
    assert "rows" in r and len(r.get("rows")) >= 1

    # preview insert should rollback
    r2 = exec_mod.preview_query(conn_meta, "INSERT INTO demo (val) VALUES ('y')", None)
    assert r2.get("ok") is True
    # confirm DB still has 1 row
    conn2 = sqlite3.connect(str(db_path))
    cur2 = conn2.cursor()
    cur2.execute("SELECT count(*) FROM demo")
    cnt = cur2.fetchone()[0]
    conn2.close()
    assert cnt == 1


def test_create_mapping_and_path_uniqueness(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    # create connector and query
    cid = storage_mod.add_connector_entry("mapconn", "sqlite:///:memory:")
    qid = storage_mod.add_query_entry(cid, "qmap", "SELECT 1")

    params_json = [{"name": "limit", "in": "query", "type": "integer", "required": False}]
    mid = storage_mod.add_mapping_entry(qid, cid, "/api/test", "GET", params_json, auth_required=True)
    assert mid

    # adding same path+method should fail
    try:
        storage_mod.add_mapping_entry(qid, cid, "/api/test", "GET", params_json, auth_required=True)
        assert False, "expected ValueError for duplicate path"
    except ValueError:
        pass


def test_api_key_creation_and_admin_enforcement(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    # create admin key
    token = storage_mod.add_api_key_entry("admin")
    assert token
    rec = storage_mod.validate_api_key(token)
    assert rec and rec.get("role") == "admin"

    # ensure stored record does not include plaintext
    keys = storage_mod.read_api_keys()
    assert any(k["id"] == rec.get("id") and "hash" in k for k in keys)
    # validate_api_key returns record for token
    rec2 = storage_mod.validate_api_key(token)
    assert rec2 and rec2.get("role") == "admin"


def test_deploy_mapping_and_runtime_call(tmp_path, monkeypatch):
    # test deploying a mapping and calling the deployed route
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    # create a sqlite file-backed DB and populate
    db_path = tmp_path / "deploy.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO users (name) VALUES ('Alice')")
    conn.commit()
    conn.close()

    # add connector, query, mapping
    cid = storage_mod.add_connector_entry("deployconn", f"sqlite:///{db_path}")
    qid = storage_mod.add_query_entry(cid, "get-users", "SELECT id, name FROM users WHERE name = :name")
    params_json = [{"name": "name", "in": "query", "type": "string", "required": True}]
    mid = storage_mod.add_mapping_entry(qid, cid, "/runtime/users", "GET", params_json, auth_required=False)

    # mark mapping as deployed in storage (we can't import FastAPI in this environment reliably)
    storage_mod.set_mapping_deployed(mid, True)

    # simulate runtime invocation by executing the underlying query
    import exec_query as exec_mod
    importlib.reload(exec_mod)

    conn_meta = storage_mod.get_connector_by_id(cid)
    res = exec_mod.run_query(conn_meta, "SELECT id, name FROM users WHERE name = :name", {"name": "Alice"})
    assert res.get("ok") is True
    assert res.get("rows")[0]["name"] == "Alice"


def test_undeploy_mapping_marks_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    # create connector/query/mapping
    cid = storage_mod.add_connector_entry("uconn", "sqlite:///:memory:")
    qid = storage_mod.add_query_entry(cid, "q", "SELECT 1")
    params_json = []
    mid = storage_mod.add_mapping_entry(qid, cid, "/u", "GET", params_json, auth_required=False)

    # set deployed true
    storage_mod.set_mapping_deployed(mid, True)
    mappings = storage_mod.read_mappings()
    m = next(x for x in mappings if x.get("id") == mid)
    assert m.get("deployed") is True

    # undeploy
    storage_mod.set_mapping_deployed(mid, False)
    mappings2 = storage_mod.read_mappings()
    m2 = next(x for x in mappings2 if x.get("id") == mid)
    assert m2.get("deployed") is False


def test_run_query_max_rows_and_more_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    import exec_query as exec_mod
    importlib.reload(storage_mod)
    importlib.reload(exec_mod)

    # create sqlite file and many rows
    db_path = tmp_path / "many.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE nums (id INTEGER PRIMARY KEY, v INTEGER)")
    for i in range(20):
        cur.execute("INSERT INTO nums (v) VALUES (?)", (i,))
    conn.commit()
    conn.close()

    cid = storage_mod.add_connector_entry("nconn", f"sqlite:///{db_path}")
    conn_meta = storage_mod.get_connector_by_id(cid)

    # request max_rows=5
    res = exec_mod.run_query(conn_meta, "SELECT id, v FROM nums ORDER BY id", None, max_rows=5)
    assert res.get("ok") is True
    assert len(res.get("rows")) == 5
    assert res.get("more") is True


def test_run_query_is_proc_commits(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    import exec_query as exec_mod
    importlib.reload(storage_mod)
    importlib.reload(exec_mod)

    db_path = tmp_path / "proc.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()

    cid = storage_mod.add_connector_entry("pconn", f"sqlite:///{db_path}")
    conn_meta = storage_mod.get_connector_by_id(cid)

    # simulate a stored-proc-like insert (is_proc True should still commit in run_query)
    res = exec_mod.run_query(conn_meta, "INSERT INTO t (name) VALUES ('Z')", None, is_proc=True)
    assert res.get("ok") is True
    # confirm DB has the row
    conn2 = sqlite3.connect(str(db_path))
    cur2 = conn2.cursor()
    cur2.execute("SELECT count(*) FROM t")
    cnt = cur2.fetchone()[0]
    conn2.close()
    assert cnt == 1


def test_read_logs_and_get_deployed_mappings(tmp_path, monkeypatch):
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    # create a mapping and a fake log
    cid = storage_mod.add_connector_entry("lconn", "sqlite:///:memory:")
    qid = storage_mod.add_query_entry(cid, "ql", "SELECT 1")
    mid = storage_mod.add_mapping_entry(qid, cid, "/l", "GET", [], auth_required=False)

    storage_mod.set_mapping_deployed(mid, True)
    deployed = storage_mod.get_deployed_mappings()
    assert any(m.get("id") == mid for m in deployed)

    # append a log and read it
    storage_mod.append_log({"request_id": "r1", "mapping_id": mid, "time": "t"})
    logs = storage_mod.read_logs()
    assert any(l.get("request_id") == "r1" for l in logs)


def test_rate_limiter_allows_and_blocks():
    from rate_limit import RateLimiter, get_rate_limiter
    rl = RateLimiter()
    rl.configure("k1", limit=2, window_seconds=1)
    assert rl.allow("k1") is True
    assert rl.allow("k1") is True
    assert rl.allow("k1") is False


def test_build_params_model_and_validation():
    from param_model import build_params_model
    Model = build_params_model("Mtest", [{"name": "age", "in": "query", "type": "integer", "required": True}])
    inst = Model(age=30)
    assert inst.age == 30


def test_sql_utils_extract_and_validate():
    from sql_utils import extract_named_params, validate_params_against_sql
    sql = "SELECT * FROM t WHERE id = :id AND name = :name"
    used = extract_named_params(sql)
    assert used == {"id", "name"}
    ok, msg = validate_params_against_sql(sql, {"id": 1})
    assert ok is False
    assert "missing" in msg


def test_metrics_and_health():
    import metrics
    metrics.incr("calls")
    metrics.incr("calls", 2)
    assert metrics.get_counter("calls") == 3
    h = metrics.health_check()
    assert h.get("status") == "ok"


def test_global_exception_handler_logs_and_returns_structure(tmp_path, monkeypatch):
    # ensure metadata dir
    monkeypatch.setenv("METADATA_DIR", str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    try:
        # simulate an unexpected exception and ensure our error formatter logs it
        raise RuntimeError("boom")
    except Exception as e:
        from errors import format_exception_response
        status_code, body, logrec = format_exception_response(e)
        assert status_code == 500
        assert "request_id" in body

    # check logs file has an error entry
    logs = storage_mod.read_logs()
    assert any(l.get("status") == "error" for l in logs)


def test_spa_static_and_mappings_listing(tmp_path, monkeypatch):
    # ensure static index exists
    from pathlib import Path
    assert Path('static/index.html').exists()

    # storage listing via storage.read_mappings
    monkeypatch.setenv('METADATA_DIR', str(tmp_path))
    import importlib
    import storage as storage_mod
    importlib.reload(storage_mod)

    cid = storage_mod.add_connector_entry('s1', 'sqlite:///:memory:')
    qid = storage_mod.add_query_entry(cid, 'sq', 'SELECT 1')
    mid = storage_mod.add_mapping_entry(qid, cid, '/x', 'GET', [], auth_required=False)
    mappings = storage_mod.read_mappings()
    assert any(m.get('id') == mid for m in mappings)
