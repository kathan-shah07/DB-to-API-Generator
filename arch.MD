Functional requirements --- user stories
======================================

**Frontend:** HTML single-page app\
**Backend:** Python (FastAPI recommended)\
**Storage:** JSON files for metadata & mappings

Each user story is short, actionable, and testable with clear acceptance criteria. Stories are grouped by epic and ordered P0 → P1.

* * * * *

Epic: Connector management (P0)
===============================

US-01 --- Add connector
---------------------

**As a** Admin\
**I want to** add a database connector by entering a name and SQLAlchemy-compatible URL (or driver details) in the HTML UI\
**So that** the tool can connect to that database to discover schema and run queries.

**Acceptance Criteria**

-   UI: form with `name`, `sqlalchemy_url` (or fields for driver/server/db/user/password).

-   On submit the frontend posts JSON to `POST /admin/connectors`.

-   Backend stores connector record in `connectors.json` with `id`, `name`, `sqlalchemy_url`, `created_at`.

-   Response returns `id` and status `created`.

* * * * *

US-02 --- Test connector
----------------------

**As a** Admin\
**I want to** test the connector to verify connectivity\
**So that** I can confirm credentials and network reachability.

**Acceptance Criteria**

-   UI provides a **Test** button next to a connector → calls `POST /admin/connectors/{id}/test`.

-   Backend attempts a lightweight `SELECT 1` (or equivalent) and returns `{ok: true, latency_ms: N}` or `{ok:false, error:"..."}`.

-   Test results shown in UI.

* * * * *

US-03 --- Edit / Delete connector
-------------------------------

**As a** Admin\
**I want to** update or remove a connector\
**So that** I can fix mistakes or decommission connectors.

**Acceptance Criteria**

-   Edit: `PUT /admin/connectors/{id}` updates `connectors.json`.

-   Delete: `DELETE /admin/connectors/{id}` removes connector; UI asks for confirmation. Deleting a connector prevents deploying new mappings and marks existing mappings as invalid.

* * * * *

Epic: Schema discovery & explorer (P0)
======================================

US-04 --- Discover schema
-----------------------

**As a** Admin\
**I want to** discover schema (tables, columns, primary keys) from a connector\
**So that** I can see what data is available to query or expose.

**Acceptance Criteria**

-   UI: **Discover** button calls `POST /admin/connectors/{id}/discover`.

-   Backend uses SQLAlchemy inspector to build a JSON snapshot and stores it in `schemas.json` with `connector_id`, `snapshot`, `created_at`.

-   Response includes list of tables and column metadata.

* * * * *

US-05 --- Explore schema and sample rows
--------------------------------------

**As a** Admin\
**I want to** view tables, columns, and sample rows (first N rows) in the HTML UI\
**So that** I can author queries and map APIs correctly.

**Acceptance Criteria**

-   UI: click table → calls `GET /admin/connectors/{id}/schema/{table}?sample=10`.

-   Backend returns columns and sample rows (max cap enforced).

-   UI displays columns and sample rows in a simple table.

* * * * *

Epic: Saved queries & stored procedure management (P0)
======================================================

US-06 --- Save a query / stored-proc template
-------------------------------------------

**As a** Admin\
**I want to** paste or author a parameterized SQL or stored-proc call and save it as `query-<n>`\
**So that** it can be reused and mapped to API endpoints.

**Acceptance Criteria**

-   UI: form with `name`, `sql_text`, `is_proc` flag, optional `description`.

-   Submit → `POST /admin/queries` stores entry in `queries.json` with `id`, `connector_id`, `sql_text`, `is_proc`, `created_at`.

-   Backend validates query contains named parameters (e.g., `:user_id`) when required and returns created id.

* * * * *

US-07 --- Preview query execution (dry-run)
-----------------------------------------

**As a** Admin\
**I want to** preview the query with test parameters without saving side effects\
**So that** I can validate parameter mapping and result shape.

**Acceptance Criteria**

-   UI: **Preview** button posts to `POST /admin/queries/preview` with `connector_id`, `sql_text`, `params`.

-   Backend executes in read-only or transaction-rolled-back mode; returns sample results or error.

-   UI shows results or descriptive error.

* * * * *

Epic: API mapping & deployment (P0)
===================================

US-08 --- Create API mapping for a saved query
--------------------------------------------

**As a** Admin\
**I want to** map a saved query to an API route (path + method) with parameter bindings\
**So that** the server can expose that query as a callable HTTP endpoint.

**Acceptance Criteria**

-   UI: mapping form with `query_id`, `path` (e.g., `/api/users/get-user`), `method` (GET/POST/PUT/DELETE), and `params_json` (`name`, `in: path/query/body/header`, `type`, `required`, `default`).

-   Submit → `POST /admin/mappings` stores mapping in `mappings.json` with `id`, `query_id`, `connector_id`, `path`, `method`, `params_json`, `auth_required`, `deployed:false`, `created_at`.

-   Backend validates path uniqueness and `params_json` correctness.

* * * * *

US-09 --- Deploy mapping (register dynamic route)
-----------------------------------------------

**As a** Admin\
**I want to** deploy a mapping so the backend dynamically registers the API route\
**So that** clients can call the new endpoint.

**Acceptance Criteria**

-   UI button **Deploy** calls `POST /admin/mappings/{id}/deploy`.

-   Backend: loads mapping, builds Pydantic model from `params_json`, uses `app.add_api_route()` to register handler closure that:

    -   validates auth if `auth_required`,

    -   extracts params from path/query/body/header,

    -   executes stored `sql_text` against the connector using named bind params,

    -   returns JSON `{status:"ok", rows:[...]}` or `{status:"ok", message}`.

-   Mapping record updated `deployed:true` in `mappings.json`.

-   Deploy response includes route path and sample curl.

* * * * *

US-10 --- Undeploy mapping (remove route)
---------------------------------------

**As a** Admin\
**I want to** undeploy a mapping so it no longer responds\
**So that** I can revoke exposure quickly.

**Acceptance Criteria**

-   UI: **Undeploy** calls `POST /admin/mappings/{id}/undeploy`.

-   Backend marks `deployed:false` and removes the dynamic route (or makes handler return 410).

-   UI reflects undeployed status.

* * * * *

Epic: Runtime API behavior (P0)
===============================

US-11 --- Call generated API endpoint
-----------------------------------

**As a** Consumer (client)\
**I want to** call the generated API endpoint with parameters\
**So that** the server runs the stored query/proc and returns results.

**Acceptance Criteria**

-   Request path/method match the deployed mapping.

-   Params validated by generated pydantic model (400 if invalid).

-   Backend executes saved query with parameter binding; returns JSON resultset up to server-side cap (e.g., `max_rows=1000`).

-   Errors return structured JSON: `{error_code, message, request_id, timestamp}` and server logs full stack.

* * * * *

US-12 --- Run stored procedure mapping
------------------------------------

**As a** Consumer\
**I want to** invoke a mapping that is a stored-proc call (possibly with side-effects)\
**So that** I can trigger server-side logic.

**Acceptance Criteria**

-   Mapping flagged `is_proc:true` in `queries.json`.

-   Backend executes `EXEC schema.proc @p1=:p1` (MSSQL) or `CALL` (Postgres) with bound params.

-   For mutating procs the response returns success metadata or resultset if proc returns rows.

-   Backend runs proc inside a transaction when appropriate and returns 200 or 4xx/5xx on failure.

* * * * *

Epic: Authentication & Authorization (P0)
=========================================

US-13 --- API key creation (admin)
--------------------------------

**As a** Admin\
**I want to** create API keys (admin and consumer) and copy them once\
**So that** clients can call endpoints and admin can manage tool.

**Acceptance Criteria**

-   UI: Create API Key form (role selection: admin/consumer).

-   Backend: `POST /admin/api-keys` generates a random token, stores only hashed token in `api_keys.json` with `id`, `role`, `hash`, `created_at`. Returns the plaintext token once to admin.

-   Admin keys required to access `/admin/*` endpoints.

* * * * *

US-14 --- Validate API key on generated endpoints
-----------------------------------------------

**As a** Consumer\
**I want to** present my API key in `X-API-Key` header to call generated APIs\
**So that** server authorizes calls.

**Acceptance Criteria**

-   Backend validates incoming `X-API-Key` against `api_keys.json`.

-   Mapping-level `auth_required` enforces that consumer keys are required; otherwise mapping can be public (rarely).

-   Unauthorized calls return 401 with `request_id`.

* * * * *

Epic: Logging, auditing & error handling (P0)
=============================================

US-15 --- Log and audit every API invocation
------------------------------------------

**As a** Admin/Auditor\
**I want to** log `request_id`, `mapping_id`, `caller_key_id` (if any), params hash, timestamp, and duration\
**So that** I can audit usage and troubleshoot.

**Acceptance Criteria**

-   Backend generates `request_id` (uuid4) for every call and logs to `logs.json` (append) or a daily file.

-   Log entry includes `mapping_id` (or `connector`+`query`), caller_key id (if authenticated), params meta (no raw sensitive values), timestamp, `duration_ms`, and `result_status`.

-   Logs are searchable by `request_id` via `GET /admin/logs/{request_id}`.

* * * * *

US-16 --- Structured error responses
----------------------------------

**As a** Consumer\
**I want to** receive structured errors with `request_id`\
**So that** I can give the id to admins to debug.

**Acceptance Criteria**

-   All errors return JSON: `{error_code, message, request_id, timestamp}`.

-   Backend logs full error stack with `request_id` for admin review.

* * * * *

Epic: UI/UX (HTML frontend) (P0)
================================

US-17 --- Single-page admin UI
----------------------------

**As a** Admin\
**I want to** manage connectors, queries and mappings from a single HTML page\
**So that** administration is simple and local.

**Acceptance Criteria**

-   `index.html` with sections / panels: Connectors, Schema Explorer, Saved Queries, Mappings, API Keys, Logs.

-   All interactions use `fetch()` to backend JSON endpoints.

-   UI shows inline validation, confirmation dialogs for destructive actions, and success/failure toasts.

* * * * *

US-18 --- Mapping list with API button
------------------------------------

**As a** Admin/Tester\
**I want to** see deployed mappings in a list with a **Test API** button next to each\
**So that** I can quickly call the generated endpoint with sample params.

**Acceptance Criteria**

-   UI shows mapping rows with `path`, `method`, `deployed` flag, and **Test** button.

-   Clicking **Test** opens a small modal to enter params and calls the endpoint; response displayed.

* * * * *

Epic: Data handling & constraints (P0)
======================================

US-19 --- Parameter validation & sanitization
-------------------------------------------

**As a** Admin/Developer\
**I want to** define param types and defaults in mappings and have server enforce them\
**So that** dangerous or malformed input is rejected before DB execution.

**Acceptance Criteria**

-   `params_json` used to dynamically build pydantic models for runtime validation.

-   Type mismatches produce 400.

-   Strings trimmed to reasonable length; numeric range checks if provided.

* * * * *

US-20 --- Row caps and pagination
-------------------------------

**As a** Consumer\
**I want to** receive paginated results and maximum row caps enforced by server\
**So that** I avoid huge payloads and DoS.

**Acceptance Criteria**

-   All list-returning mappings accept `limit`/`offset` (default `limit <= 100`).

-   Server enforces `max_limit` (configurable) and truncates if necessary.

* * * * *

Epic: Maintenance & operations (P1)
===================================

US-21 --- Export / Import metadata (JSON)
---------------------------------------

**As a** Admin\
**I want to** export connectors/queries/mappings as JSON and import them later\
**So that** I can backup or move configuration.

**Acceptance Criteria**

-   `GET /admin/export` returns a ZIP/JSON bundle of `connectors.json`, `queries.json`, `mappings.json`, `api_keys.json`.

-   `POST /admin/import` accepts such a bundle and restores entries (with id collision rules).

* * * * *

US-22 --- Versioned query snapshots
---------------------------------

**As a** Admin\
**I want to** keep versions of saved queries when edited\
**So that** I can roll back if needed.

**Acceptance Criteria**

-   Edit of a saved query creates a new version entry in `queries.json` (store history). UI shows version list and rollback button.

* * * * *

Non-functional acceptance notes (applies to P0 stories)
=======================================================

-   All admin endpoints require an admin API key header `X-API-Key`.

-   All metadata stored as JSON files in a configurable folder (e.g., `./metadata/connectors.json`, `queries.json`, `mappings.json`, `api_keys.json`, `logs.json`). Backend must write atomically to avoid corruption (`write -> fsync -> rename`).

-   Backend must never store plaintext API keys (store bcrypt hashes) --- but return plaintext only once on creation. For JSON storage, include only hashed secrets.

-   All DB executions must use parameter binding (SQLAlchemy `text()` + bound params). The server must not allow runtime raw-SQL execution except for stored queries that were saved by Admin.

-   Limit default row returns to prevent large memory usage (configurable `MAX_ROWS=1000`).

-   Provide easy dev mode: `DEV_MODE=true` disables encryption and uses local SQLite/SQLite-like connectors for quick testing.

* * * * *

Minimal test cases (for each P0 story)
======================================

-   Add connector → test returns ok.

-   Discover schema → snapshot contains expected tables and columns.

-   Save query → `queries.json` contains new entry and id returned.

-   Create mapping with invalid path or conflicting path → 400.

-   Deploy mapping → `mappings.json` `deployed:true` and app responds to path.

-   Call mapping with missing param → 400.

-   Call mapping with correct param → 200 and correct rows.

-   Create API key → returned plaintext visible once; subsequent lookup returns only hash.

-   Unauthorized admin call → 401.

-   Preview query returns result but does not change DB (transaction rollback or read-only).

* * * * *

*End of file.*