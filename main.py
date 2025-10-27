from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import storage
import dbtest
import discover
import exec_query
from fastapi import Depends, Request
import os
from pydantic import BaseModel
from fastapi.responses import JSONResponse, HTMLResponse
import traceback
import uuid
import datetime
from fastapi.staticfiles import StaticFiles
import param_model


app = FastAPI(title="DB API Admin")

# serve static files under /static and root index
app.mount("/static", StaticFiles(directory="./static"), name="static")


@app.get("/")
def index():
    html = open("static/index.html", "r", encoding="utf-8").read()
    return HTMLResponse(content=html, status_code=200)


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

    # if already deployed, be idempotent
    if mapping.get("deployed"):
        return {"id": mapping_id, "status": "already_deployed"}

    # build pydantic model from params_json using param_model helper
    params_json = mapping.get("params_json", [])
    Model = None
    try:
        Model = param_model.build_params_model("ParamsModel_" + mapping_id, params_json)
    except Exception:
        Model = None

    # create handler
    async def handler(request: Request, **path_params):
        # gather params
        data = {}
        # path params
        data.update(path_params)
        # query params
        for k, v in request.query_params.items():
            if k not in data:
                data[k] = v
        # headers (only those defined in params_json as in: header)
        for name in request.headers.keys():
            if name in data:
                continue
            # lower-case header names if needed

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
        try:
            validated = Model(**data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

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

        # prepare params dict for SQL execution; remove pagination fields
        try:
            params = validated.model_dump(exclude={"limit", "offset"})
        except Exception:
            # fallback for non-pydantic models
            params = {k: getattr(validated, k) for k in getattr(validated, "__dict__", {}).keys() if k not in ("limit", "offset")}

        # enforce max limit if provided
        if hasattr(validated, "limit") and validated.limit is not None:
            if validated.limit > MAX_LIMIT:
                validated.limit = MAX_LIMIT

        # use exec_query.run_query to execute and measure duration
        import time, uuid
        start = time.time()
        res = exec_query.run_query(connector, q.get("sql_text"), params, max_rows=validated.limit if hasattr(validated, "limit") else 100, is_proc=bool(q.get("is_proc")))
        duration_ms = int((time.time() - start) * 1000)

        # log
        rid = uuid.uuid4().hex
        logrec = {
            "request_id": rid,
            "mapping_id": mapping_id,
            "time": __import__("datetime").datetime.utcnow().isoformat() + "Z",
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

        # include more hint if provided by run_query
        more = res.get("more", False)
        response = {"request_id": rid, "duration_ms": duration_ms, "result": res}
        if more:
            response["more"] = True
        return response

    # register route
    path = mapping.get("path")
    method = mapping.get("method", "GET").upper()
    # FastAPI expects uppercase methods list
    app.add_api_route(path, handler, methods=[method])
    # persist deployed flag
    storage.set_mapping_deployed(mapping_id, True)
    # keep in memory registry
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


@app.get("/admin/logs/{request_id}")
def get_log(request_id: str, admin=Depends(require_admin)):
    logs = storage.read_logs()
    rec = next((l for l in logs if l.get("request_id") == request_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="log not found")
    return rec


def register_deployed_routes(app_instance: FastAPI):
    """Register all mappings that are marked deployed in storage into the provided FastAPI app.

    This is safe to call at startup; it will attempt to build models and handlers just like the deploy endpoint.
    """
    mappings = storage.get_deployed_mappings()
    for mapping in mappings:
        mid = mapping.get("id")
        # skip if already registered in this process
        if mid in _deployed_routes:
            continue

        # build model (reuse same logic)
        params_json = mapping.get("params_json", [])
        from pydantic import create_model
        fields = {}
        type_map = {"string": (str, ...), "integer": (int, ...), "number": (float, ...), "boolean": (bool, ...)}
        for p in params_json:
            fname = p.get("name")
            ptype = p.get("type")
            required = p.get("required", True)
            default = p.get("default", ... if required else None)
            tp = type_map.get(ptype, (str, ...))
            if required:
                fields[fname] = (tp[0], default)
            else:
                fields[fname] = (tp[0], None)
        try:
            Model = create_model("ParamsModel_" + mid, **fields)
        except Exception:
            Model = None

        # create handler similar to deploy
        async def handler(request: Request, **path_params):
            data = {}
            data.update(path_params)
            for k, v in request.query_params.items():
                if k not in data:
                    data[k] = v
            try:
                body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
            except Exception:
                body = {}
            if isinstance(body, dict):
                for k, v in body.items():
                    if k not in data:
                        data[k] = v

            if Model:
                try:
                    validated = Model(**data)
                except Exception:
                    raise HTTPException(status_code=400, detail="invalid params")
            else:
                validated = type("_V", (), {})()

            # simple auth
            if mapping.get("auth_required"):
                key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
                rec = storage.validate_api_key(key)
                if not rec:
                    raise HTTPException(status_code=401, detail="missing or invalid api key")

            # execute underlying query
            qid = mapping.get("query_id")
            queries = storage.read_queries()
            q = next((x for x in queries if x.get("id") == qid), None)
            if not q:
                raise HTTPException(status_code=500, detail="query missing")
            connector = storage.get_connector_by_id(mapping.get("connector_id"))
            if not connector:
                raise HTTPException(status_code=500, detail="connector missing")

            params = {}
            if Model:
                try:
                    params = validated.model_dump(exclude={"limit", "offset"})
                except Exception:
                    params = {k: getattr(validated, k) for k in getattr(validated, "__dict__", {}).keys() if k not in ("limit", "offset")}
            # determine max_rows from model/defaults
            max_rows = 100
            if Model and hasattr(validated, "limit"):
                max_rows = min(getattr(validated, "limit", 100) or 100, MAX_LIMIT)

            res = exec_query.run_query(connector, q.get("sql_text"), params, max_rows=max_rows, is_proc=bool(q.get("is_proc")))
            if not res.get("ok"):
                raise HTTPException(status_code=500, detail=res.get("error"))
            return res

        # register route
        try:
            app_instance.add_api_route(mapping.get("path"), handler, methods=[mapping.get("method", "GET")])
            _deployed_routes[mid] = {"path": mapping.get("path"), "method": mapping.get("method", "GET")}
        except Exception:
            # ignore registration failures; admin can redeploy later
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
