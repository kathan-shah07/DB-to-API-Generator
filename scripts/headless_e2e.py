"""Headless end-to-end verification script.
Runs the core flows without starting the FastAPI server so it avoids FastAPI/Pydantic import-time issues.

It will:
 - create a temporary METADATA_DIR
 - create a sqlite file DB and the needed table
 - add connector via storage
 - add query via storage
 - add mapping via storage
 - mark mapping as deployed (storage.set_mapping_deployed)
 - simulate calling the mapping by building a param model with param_model and running exec_query.run_query
 - append and print a log entry

Run:
  .\.venv\Scripts\python.exe .\scripts\headless_e2e.py

"""
import os
import sys
import tempfile
import sqlite3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import storage
import exec_query
import param_model


def run():
    with tempfile.TemporaryDirectory() as td:
        print("Using temp METADATA_DIR:", td)
        os.environ["METADATA_DIR"] = td
        # reload storage module to pick up METADATA_DIR if necessary
        import importlib
        importlib.reload(storage)

        # create sqlite DB file
        db_path = Path(td) / "headless.db"
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
        cur.execute("INSERT INTO people (name, age) VALUES (?,?)", ("Alice", 30))
        cur.execute("INSERT INTO people (name, age) VALUES (?,?)", ("Bob", 25))
        conn.commit(); conn.close()

        # add connector
        cid = storage.add_connector_entry("headless_sqlite", f"sqlite:///{db_path}")
        print("connector id:", cid)

        # add query
        qid = storage.add_query_entry(cid, "get_person", "SELECT id, name, age FROM people WHERE name = :name", is_proc=False)
        print("query id:", qid)

        # add mapping
        params_json = [{"name": "name", "in": "query", "type": "string", "required": True}]
        mid = storage.add_mapping_entry(qid, cid, "/headless/find", "GET", params_json, auth_required=False)
        print("mapping id:", mid)

        # mark mapping deployed
        storage.set_mapping_deployed(mid, True)
        print("marked mapping deployed")

        # simulate runtime call
        mapping = next(m for m in storage.read_mappings() if m.get("id") == mid)
        queries = storage.read_queries()
        q = next(x for x in queries if x.get("id") == qid)
        connector = storage.get_connector_by_id(cid)

        # build model and validate params
        Model = param_model.build_params_model("M_"+mid, mapping.get("params_json", []))
        try:
            validated = Model(name="Alice")
            try:
                print("validated params:", validated.model_dump())
            except Exception:
                print("validated params:", getattr(validated, "__dict__", {}))
        except Exception as e:
            print("validation failed:", e)
            return 1

        # prepare params (strip pagination)
        try:
            params = validated.model_dump(exclude={"limit", "offset"})
        except Exception:
            params = {k: getattr(validated, k) for k in getattr(validated, "__dict__", {}).keys() if k not in ("limit", "offset")}
        print("exec params:", params)

        res = exec_query.run_query(connector, q.get("sql_text"), params, max_rows=100, is_proc=bool(q.get("is_proc")))
        print("exec result:", json.dumps(res, indent=2))

        # append a log
        import uuid, datetime
        rid = uuid.uuid4().hex
        logrec = {"request_id": rid, "mapping_id": mid, "time": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "ok" if res.get("ok") else "error", "params": {"name": "Alice"}}
        storage.append_log(logrec)
        print("appended log", logrec)

        # show logs file
        logs = storage.read_logs()
        print("logs:", json.dumps(logs, indent=2))

    return 0

if __name__ == "__main__":
    raise SystemExit(run())
