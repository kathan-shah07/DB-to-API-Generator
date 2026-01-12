import os
import sys
import uuid
import datetime
import traceback
from typing import List, Optional

# Add the backend directory to sys.path to allow relative imports of local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import storage
import dbtest
import discover
import exec_query
import param_model


app = FastAPI(title="DB API Admin")

# serve React frontend if built, else fallback
# serve React frontend if built, else fallback
# We look for frontend in the parent directory of this backend folder
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dist = os.path.join(base_dir, "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    app.mount("/dist", StaticFiles(directory=frontend_dist), name="dist")

    @app.get("/")
    def index():
        return HTMLResponse(open(os.path.join(frontend_dist, "index.html"), encoding="utf-8").read(), status_code=200)
else:
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="./static"), name="static")

    @app.get("/")
    def index():
        if os.path.exists("static/index.html"):
            return HTMLResponse(open("static/index.html", encoding="utf-8").read(), status_code=200)
        return {"message": "No frontend found. Build the React app or check static/ folder."}


@app.get("/guide", response_class=HTMLResponse)
def get_guide():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    guide_path = os.path.join(base_dir, "demo", "DEMO_GUIDE.html")
    if os.path.exists(guide_path):
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Guide not found")


# runtime route registry (in-memory)
_deployed_routes = {}

# maximum limit enforced for list-returning mappings
MAX_LIMIT = 100


def require_admin(request: Request):
    # Allow a DEV_MODE override for convenient local testing. When DEV_MODE is truthy
    # the admin check is bypassed and a dev admin record is returned.
    if os.environ.get("DEV_MODE", "").lower() in ("1", "true", "yes"):
        return {"id": "dev-admin", "role": "admin"}

    key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(status_code=401, detail="missing api key")
    rec = storage.validate_api_key(key)
    if not rec:
        raise HTTPException(status_code=401, detail="invalid api key")
    if rec.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return rec


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return structured error JSON and log full stack with a request_id.

    Format: {error_code, message, request_id, timestamp}
    """
    # generate request id and timestamp
    rid = uuid.uuid4().hex
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        message = exc.detail if hasattr(exc, "detail") else str(exc)
        error_code = f"HTTP_{status_code}"
    else:
        status_code = 500
        message = str(exc) or exc.__class__.__name__
        error_code = "INTERNAL_ERROR"

    # format full stack trace
    try:
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        stack = "<no traceback available>"

    # append structured log entry (best-effort)
    logrec = {
        "request_id": rid,
        "time": ts,
        "status": "error",
        "error_code": error_code,
        "message": message,
        "stack": stack,
    }
    try:
        storage.append_log(logrec)
    except Exception:
        # don't let logging failure mask original error
        pass

    body = {"error_code": error_code, "message": message, "request_id": rid, "timestamp": ts}
    return JSONResponse(status_code=status_code, content=body)


class ConnectorIn(BaseModel):
    name: str
    sqlalchemy_url: str


class ConnectorOut(BaseModel):
    id: str
    status: str


class TestResult(BaseModel):
    ok: bool
    latency_ms: int | None = None
    error: str | None = None


class DiscoverOut(BaseModel):
    connector_id: str
    tables: dict


class QueryIn(BaseModel):
    connector_id: str
    name: str
    sql_text: str
    is_proc: bool = False
    description: str | None = None


class QueryOut(BaseModel):
    id: str


class PreviewIn(BaseModel):
    connector_id: str
    sql_text: str
    params: dict | None = None
    max_rows: int | None = 10


@app.post("/admin/queries/preview")
def preview_query(payload: PreviewIn, admin=Depends(require_admin)):
    c = storage.get_connector_by_id(payload.connector_id)
    if not c:
        raise HTTPException(status_code=404, detail="connector not found")

    res = exec_query.preview_query(c, payload.sql_text, payload.params or {}, max_rows=payload.max_rows or 10)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.get("/admin/drivers/odbc")
def get_odbc_drivers(admin=Depends(require_admin)):
    try:
        import pyodbc
        return pyodbc.drivers()
    except Exception:
        return []


class MappingIn(BaseModel):
    query_id: str
    connector_id: str
    path: str
    method: str
    params_json: list
    auth_required: bool = True


class MappingOut(BaseModel):
    id: str


@app.post("/admin/mappings", response_model=MappingOut, status_code=201)
def add_mapping(payload: MappingIn, admin=Depends(require_admin)):
    try:
        mid = storage.add_mapping_entry(payload.query_id, payload.connector_id, payload.path, payload.method, payload.params_json, payload.auth_required)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": mid}


@app.post("/admin/mappings/{mapping_id}/deploy")
def deploy_mapping(mapping_id: str, admin=Depends(require_admin)):
    # locate mapping
    mappings = storage.read_mappings()
    mapping = next((m for m in mappings if m.get("id") == mapping_id), None)
    if not mapping:
        raise HTTPException(status_code=404, detail="mapping not found")

    # even if already marked deployed in storage, we ensure it's in the router
    # but first remove any existing registration for this specific mapping path/method
    path = mapping.get("path")
    method = mapping.get("method", "GET").upper()

    # remove matching route(s) from app.router to avoid duplicates or disabled stubs
    new_routes = []
    for r in app.router.routes:
        try:
            if getattr(r, "path", None) == path and method in getattr(r, "methods", set()):
                continue
        except Exception:
            pass
        new_routes.append(r)
    app.router.routes = new_routes

    # build pydantic model from params_json using param_model helper
    params_json = mapping.get("params_json", [])
    Model = None
    try:
        Model = param_model.build_params_model("ParamsModel_" + mapping_id, params_json)
    except Exception:
        Model = None

def create_mapping_handler(mapping, Model):
    mapping_id = mapping.get("id")
    
    async def handler(request: Request):
        # gather params
        data = {}
        # path params
        data.update(request.path_params)
        # query params
        for k, v in request.query_params.items():
            if k not in data:
                data[k] = v

        # body
        try:
            body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        except Exception:
            body = {}
        if isinstance(body, dict):
            for k, v in body.items():
                if k not in data:
                    data[k] = v

        # validate via model
        if Model:
            try:
                validated = Model(**data)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            # Fallback for dynamic models that failed to build
            validated = type("DynamicModel", (), data)()

        # auth enforcement
        if mapping.get("auth_required"):
            key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
            rec = storage.validate_api_key(key)
            if not rec:
                raise HTTPException(status_code=401, detail="missing or invalid api key")

        # execute query
        qid = mapping.get("query_id")
        queries = storage.read_queries()
        q = next((x for x in queries if x.get("id") == qid), None)
        if not q:
            raise HTTPException(status_code=500, detail="query missing")

        connector = storage.get_connector_by_id(mapping.get("connector_id"))
        if not connector:
            raise HTTPException(status_code=500, detail="connector missing")

        # prepare params dict for SQL execution
        try:
            params = validated.model_dump(exclude={"limit", "offset"})
        except Exception:
            params = {k: v for k, v in data.items() if k not in ("limit", "offset")}

        # enforce max limit
        limit = getattr(validated, "limit", 100) or 100
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        start = datetime.datetime.now()
        res = exec_query.run_query(connector, q.get("sql_text"), params, max_rows=limit, is_proc=bool(q.get("is_proc")))
        duration_ms = int((datetime.datetime.now() - start).total_seconds() * 1000)

        # log
        rid = uuid.uuid4().hex
        logrec = {
            "request_id": rid,
            "mapping_id": mapping_id,
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "ok" if res.get("ok") else "error",
            "duration_ms": duration_ms,
            "params": params,
        }
        if res.get("rows") is not None:
            logrec["rows_count"] = len(res.get("rows"))
        if not res.get("ok"):
            logrec["error"] = res.get("error")
        storage.append_log(logrec)

        if not res.get("ok"):
            raise HTTPException(status_code=500, detail=res.get("error"))

        return {"request_id": rid, "duration_ms": duration_ms, "result": res, "more": res.get("more", False)}

    return handler


@app.post("/admin/mappings/{mapping_id}/deploy")
def deploy_mapping(mapping_id: str, admin=Depends(require_admin)):
    mappings = storage.read_mappings()
    mapping = next((m for m in mappings if m.get("id") == mapping_id), None)
    if not mapping:
        raise HTTPException(status_code=404, detail="mapping not found")

    path = mapping.get("path")
    method = mapping.get("method", "GET").upper()

    # remove existing
    app.router.routes = [r for r in app.router.routes if not (getattr(r, "path", None) == path and method in getattr(r, "methods", set()))]

    try:
        Model = param_model.build_params_model("ParamsModel_" + mapping_id, mapping.get("params_json", []))
    except Exception:
        Model = None

    handler = create_mapping_handler(mapping, Model)
    app.add_api_route(path, handler, methods=[method])
    storage.set_mapping_deployed(mapping_id, True)
    _deployed_routes[mapping_id] = {"path": path, "method": method}

    return {"id": mapping_id, "status": "deployed", "path": path, "method": method}

@app.post("/admin/mappings/{mapping_id}/undeploy")
def undeploy_mapping(mapping_id: str, admin=Depends(require_admin)):
    # find mapping
    mappings = storage.read_mappings()
    mapping = next((m for m in mappings if m.get("id") == mapping_id), None)
    if not mapping:
        raise HTTPException(status_code=404, detail="mapping not found")

    # attempt to remove route from app.router
    reg = _deployed_routes.get(mapping_id)
    if reg:
        path = reg.get("path")
        method = reg.get("method")
        # remove matching route(s)
        new_routes = []
        removed = False
        for r in app.router.routes:
            try:
                if getattr(r, "path", None) == path and method in getattr(r, "methods", set()):
                    removed = True
                    continue
            except Exception:
                pass
            new_routes.append(r)
        if removed:
            app.router.routes = new_routes
        _deployed_routes.pop(mapping_id, None)

    # mark as undeployed in storage
    storage.set_mapping_deployed(mapping_id, False)

    # as a safety, register a disabled stub that returns 410 to avoid stale clients hitting old handlers
    async def disabled_stub():
        raise HTTPException(status_code=410, detail="mapping undeployed")

    # register stub at same path+method so the path is intentionally unavailable
    try:
        app.add_api_route(mapping.get("path"), disabled_stub, methods=[mapping.get("method", "GET")])
    except Exception:
        # ignore if adding fails
        pass

    return {"id": mapping_id, "status": "undeployed"}

@app.delete("/admin/mappings/{mapping_id}")
def remove_mapping(mapping_id: str, admin=Depends(require_admin)):
    # first undeploy if deployed
    undeploy_mapping(mapping_id, admin)
    
    ok = storage.delete_mapping(mapping_id)
    if not ok:
        raise HTTPException(status_code=404, detail="mapping not found")
    return {"status": "deleted", "id": mapping_id}


@app.get("/admin/logs/{request_id}")
def get_log(request_id: str, admin=Depends(require_admin)):
    logs = storage.read_logs()
    rec = next((l for l in logs if l.get("request_id") == request_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="log not found")
    return rec


def register_deployed_routes(app_instance: FastAPI):
    mappings = storage.get_deployed_mappings()
    for mapping in mappings:
        mid = mapping.get("id")
        if mid in _deployed_routes:
            continue

        try:
            Model = param_model.build_params_model("ParamsModel_" + mid, mapping.get("params_json", []))
        except Exception:
            Model = None

        handler = create_mapping_handler(mapping, Model)
        try:
            app_instance.add_api_route(mapping.get("path"), handler, methods=[mapping.get("method", "GET")])
            _deployed_routes[mid] = {"path": mapping.get("path"), "method": mapping.get("method", "GET")}
        except Exception:
            continue


@app.get("/admin/mappings")
def list_mappings(admin=Depends(require_admin)):
    return storage.read_mappings()


@app.get("/admin/debug/routes")
def list_registered_routes(admin=Depends(require_admin)):
    """Return a list of currently registered routes (path and methods) for debugging."""
    out = []
    for r in app.router.routes:
        try:
            path = getattr(r, "path", None)
            methods = sorted([m for m in getattr(r, "methods", []) if m not in ("HEAD", "OPTIONS")])
            out.append({"path": path, "methods": methods, "name": getattr(r, "name", None)})
        except Exception:
            continue
    return out


# Apply admin requirement to admin routes by adding dependency where appropriate.
# For simplicity we will add the dependency manually to admin endpoints below when needed.


@app.post("/admin/queries", response_model=QueryOut, status_code=201)
def add_query(payload: QueryIn, admin=Depends(require_admin)):
    try:
        qid = storage.add_query_entry(payload.connector_id, payload.name, payload.sql_text, payload.is_proc, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": qid}


@app.delete("/admin/queries/{query_id}")
def remove_query(query_id: str, admin=Depends(require_admin)):
    ok = storage.delete_query(query_id)
    if not ok:
        raise HTTPException(status_code=404, detail="query not found")
    return {"status": "deleted", "id": query_id}


@app.get("/admin/queries")
def list_queries(admin=Depends(require_admin)):
    """Return list of saved queries."""
    return storage.read_queries()


@app.post("/admin/connectors", response_model=ConnectorOut, status_code=201)
def add_connector(payload: ConnectorIn, admin=Depends(require_admin)):
    try:
        new_id = storage.add_connector_entry(payload.name, payload.sqlalchemy_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": new_id, "status": "created"}


@app.get("/admin/connectors")
def list_connectors(admin=Depends(require_admin)):
    return storage.read_connectors()


@app.post("/admin/connectors/{connector_id}/test", response_model=TestResult)
def test_connector(connector_id: str, admin=Depends(require_admin)):
    c = storage.get_connector_by_id(connector_id)
    if not c:
        raise HTTPException(status_code=404, detail="connector not found")

    result = dbtest.test_connection(c.get("sqlalchemy_url"))
    if result.get("ok"):
        return TestResult(ok=True, latency_ms=result.get("latency_ms"))
    else:
        return TestResult(ok=False, latency_ms=None, error=result.get("error"))


class ConnectorUpdate(BaseModel):
    name: str | None = None
    sqlalchemy_url: str | None = None


@app.put("/admin/connectors/{connector_id}")
def edit_connector(connector_id: str, payload: ConnectorUpdate, admin=Depends(require_admin)):
    updated = storage.update_connector(connector_id, payload.name, payload.sqlalchemy_url)
    if not updated:
        raise HTTPException(status_code=404, detail="connector not found")
    return updated


@app.delete("/admin/connectors/{connector_id}")
def remove_connector(connector_id: str, admin=Depends(require_admin)):
    ok = storage.delete_connector(connector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="connector not found")
    return {"status": "deleted", "id": connector_id}


@app.post("/admin/connectors/{connector_id}/discover")
def discover_connector(connector_id: str, sample: int = 5, admin=Depends(require_admin)):
    c = storage.get_connector_by_id(connector_id)
    if not c:
        raise HTTPException(status_code=404, detail="connector not found")

    try:
        snapshot = discover.discover_schema(c.get("sqlalchemy_url"), sample_rows=sample)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    record = storage.write_schema_snapshot(connector_id, snapshot)
    # Return table metadata (columns, pk, sample_rows) as required by US-04
    return {"connector_id": connector_id, "tables": snapshot.get("tables", {}), "snapshot_id": record.get("id")}


@app.get("/admin/connectors/{connector_id}/schema/{table}")
def get_table_schema(connector_id: str, table: str, sample: int = 10, admin=Depends(require_admin)):
    # enforce max cap
    MAX_SAMPLE = 100
    if sample > MAX_SAMPLE:
        sample = MAX_SAMPLE

    c = storage.get_connector_by_id(connector_id)
    if not c:
        raise HTTPException(status_code=404, detail="connector not found")

    try:
        info = discover.get_table_info(c.get("sqlalchemy_url"), table, sample_rows=sample)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return info



class ApiKeyIn(BaseModel):
    role: str = "consumer"


class ApiKeyOut(BaseModel):
    token: str


@app.post("/admin/api-keys", response_model=ApiKeyOut, status_code=201)
def create_api_key(payload: ApiKeyIn, admin=Depends(require_admin)):
    try:
        token = storage.add_api_key_entry(payload.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"token": token}

# Startup logic: Register already deployed routes from storage
register_deployed_routes(app)
