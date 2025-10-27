"""A small end-to-end script that starts a server process (uvicorn) and exercises the typical admin flows
using httpx. This is intended as a convenience script for local testing. It attempts to be robust if
Pydantic import-time issues prevent importing FastAPI in test runners: it uses HTTP requests to the
running server.

Usage (PowerShell):
    .\.venv\Scripts\python.exe .\scripts\e2e_test.py

It will:
 - start uvicorn main:app
 - wait for server
 - create admin key via POST /admin/api-keys (requires existing admin key; so first create one manually with create_admin_key.py or run the create_admin_key endpoint using storage helper)
 - create connector, query, mapping, deploy mapping, call runtime endpoint, fetch log

Note: For simplicity this script will assume you have already generated an admin token using
scripts/create_admin_key.py and exported it into the environment variable ADMIN_TOKEN.
"""
import os
import time
import subprocess
import sys
import json
import httpx
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UVICORN_CMD = [sys.executable, "-m", "uvicorn", "main:app", "--reload"]


def wait_for_server(url="http://127.0.0.1:8000", timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.2)
    return False


def run():
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        print("Please set ADMIN_TOKEN env var by running scripts/create_admin_key.py first")
        return 1

    # start server
    print("Starting uvicorn server...")
    proc = subprocess.Popen(UVICORN_CMD, cwd=str(ROOT))
    try:
        ok = wait_for_server()
        if not ok:
            print("server did not start")
            proc.terminate()
            return 1

        headers = {"X-API-Key": admin_token, "Content-Type": "application/json"}
        client = httpx.Client(headers=headers)

        # 1) Create a connector
        print("Creating connector (sqlite file)")
        resp = client.post("http://127.0.0.1:8000/admin/connectors", json={"name": "e2e_sqlite", "sqlalchemy_url": "sqlite:///./sample.db"})
        print(resp.status_code, resp.text)
        cid = resp.json().get("id")

        # 2) Discover
        print("Discovering schema (may be empty)")
        resp = client.post(f"http://127.0.0.1:8000/admin/connectors/{cid}/discover")
        print(resp.status_code, resp.text)

        # 3) Create a simple table in sample.db for queries
        import sqlite3
        sqlite_path = str(ROOT / "sample.db")
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS e2e (id INTEGER PRIMARY KEY, name TEXT)")
        cur.execute("INSERT INTO e2e (name) VALUES ('bob')")
        conn.commit(); conn.close()

        # 4) Create query
        print("Creating query")
        resp = client.post("http://127.0.0.1:8000/admin/queries", json={"connector_id": cid, "name": "q_e2e", "sql_text": "SELECT id, name FROM e2e WHERE name = :name", "is_proc": False})
        print(resp.status_code, resp.text)
        qid = resp.json().get("id")

        # 5) Create mapping
        print("Creating mapping")
        params = [{"name": "name", "in": "query", "type": "string", "required": True}]
        resp = client.post("http://127.0.0.1:8000/admin/mappings", json={"query_id": qid, "connector_id": cid, "path": "/e2e/find", "method": "GET", "params_json": params, "auth_required": False})
        print(resp.status_code, resp.text)
        mid = resp.json().get("id")

        # 6) Deploy mapping
        print("Deploying mapping")
        resp = client.post(f"http://127.0.0.1:8000/admin/mappings/{mid}/deploy")
        print(resp.status_code, resp.text)

        # 7) Call runtime endpoint
        print("Calling runtime endpoint")
        rt = httpx.get("http://127.0.0.1:8000/e2e/find", params={"name": "bob"})
        print(rt.status_code, rt.text)

        # 8) Read logs if request_id present in response
        try:
            body = rt.json()
            rid = body.get("request_id")
            if rid:
                print("Fetching log", rid)
                resp = client.get(f"http://127.0.0.1:8000/admin/logs/{rid}")
                print(resp.status_code, resp.text)
        except Exception:
            pass

    finally:
        print("Stopping server")
        proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
