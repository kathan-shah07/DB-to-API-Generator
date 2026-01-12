# 🏗 System Architecture: DB-to-API Generator

This document outlines the architectural design, component interaction, and data flow of the DB-to-API Generator.

---

## 🏗 Consolidated System Overview

This simplified view shows how the frontend, backend engine, and your databases are linked.

```text
    [ MANAGERS ]            [ THE BRAIN ]              [ DATA SOURCES ]
   (React Admin)          (FastAPI Engine)              (External DBs)
  +--------------+        +----------------+          +----------------+
  |  Connectors  +------> | Route Registry | +------> |   MS SQL Srv   |
  +--------------+        +-------+--------+          +----------------+
  |   Queries    +------> | SQL Executor   | +------> |   Postgres     |
  +--------------+        +-------+--------+          +----------------+
  |   Mappings   +------> | Param Model    | +------> |   SQLite       |
  +--------------+        +-------+--------+          +----------------+
                                  |
                          +-------v-------+
                          |  JSON Storage |
                          | (Persistence) |
                          +---------------+
```

---

## 🛰 System Overview

## 🏗 Component-Wise Architecture

### 💻 Frontend Architecture (React SPA)
The frontend is responsible for the management console where users configure their APIs.

```text
+-----------------------------------------------------------+
|                   FRONTEND COMPONENTS (React)             |
+-----------------------------------------------------------+
|                                                           |
|  [ Dashboard ] <---> [ Connectors ] <---> [ Queries ]     |
|      (Summary)       (DB Configs)        (SQL Editor)     |
|          ^                                  ^             |
|          |                [ Mappings ]      |             |
|          +--------------> (API Builder) <---+             |
|                                                           |
+----------------------------+------------------------------+
                             |
                   +---------v---------+
                   |  API Client (js)  | <--- (Handles Auth & JSON)
                   +---------+---------+
```

### ⚙️ Backend Architecture (FastAPI & Engine)
The backend manages metadata and dynamically handles incoming API requests.

```text
+-----------------------------------------------------------+
|                   BACKEND SERVICES (FastAPI)              |
+-----------------------------------------------------------+
|                                                           |
|  +-------------------+        +------------------------+  |
|  |   Admin Router    |        |  Dynamic Route Registry |  |
|  | (/admin/* routes) |        | (User defined endpoints)|  |
|  +---------+---------+        +-----------+------------+  |
|            |                              |               |
|  +---------v---------+        +-----------v------------+  |
|  |  Storage Handler  |        |  Param Model Builder   |  |
|  | (JSON Persistence)|        |   (Pydantic Validation)|  |
|  +---------+---------+        +-----------+------------+  |
|            |                              |               |
|            |                  +-----------v------------+  |
|            |                  |   Query Execution      |  |
|            +------------------>   (SQLAlchemy Core)    |  |
|                               +-----------+------------+  |
|                                           |               |
+-------------------------------------------+---------------+
```

---

## 📊 Combined System Journey

This diagram shows how a user interacts with the system to turn a database into an API.

```text
       USER                     FRONTEND                     BACKEND                  DATABASE
        |                          |                            |                        |
(1) Create Connector ------------> |                            |                        |
        |      (Credentials)       | ---- (POST /connectors)--> |                        |
        |                          |                            | -- (SQLAlchemy Test)-> |
        |                          | <------- (Success) ------- |                        |
        |                          |                            |                        |
(2) Define Query ----------------> |                            |                        |
        |      (SQL text)          | ------ (POST /queries) --> |                        |
        |                          |                            |                        |
(3) Map API Path ----------------> |                            |                        |
        | (/api/users/{id})        | ----- (POST /mappings) --> |                        |
        |                          |                            | -- (Build Pydantic) -- |
        |                          |                            | -- (Register Route) -- |
        |                          |                            |                        |
(4) API Consumer Request --------> |                     [ LIVE ENDPOINT ]               |
        |      (HTTP GET)          |                            | -- (Safe SQL Exec) --> |
        | <----------------------- | <--- (JSON Response) ----- |                        |
```

---

## 🧩 Core Components Deep-Dive

### 1. The Admin API (`main.py`)
The primary interface for the frontend. It handles:
- **Connector Management**: CRUD for database connection strings.
- **Query Management**: Saving SQL templates.
- **API Mapping**: Defining paths, methods, and parameter validation.
- **Lifecycle**: Real-time deployment/undeployment of routes into the running FastAPI app.

### 2. The Dynamic Route Engine (`main.py` + `param_model.py`)
The most critical part of the system.
- When an API is "Deployed", the system uses `pydantic` to build a **Runtime Validation Model**.
- It injects a generic handler into the FastAPI app's route table.
- **Security**: Wraps every call in an admin-key validation layer (if configured).

### 3. Execution Engine (`exec_query.py` + `dbtest.py`)
- **Safety**: Uses SQLAlchemy's `text()` and parameter binding to prevent SQL Injection.
- **Transaction Control**: Implements `session.rollback()` for previews to ensure "Read-Only" safety during testing, while allowing commits during live API calls.
- **Drivers**: Leverages `pyodbc` for MSSQL and `sqlite3`/`psycopg2` for others.

### 4. Storage & Persistence (`storage.py`)
- **Atomic JSON**: Instead of a heavy database for metadata, it uses lightweight JSON files with atomic write operations (`os.replace`).
- **Isolation**: Each execution run can be isolated using the `METADATA_DIR` environment variable.

---

## 🗄 Data Model (Metadata)

The system manages three primary entities stored in `metadata/`:

1.  **Connectors**: `{id, name, sqlalchemy_url}`
2.  **Queries**: `{id, connector_id, name, sql_text, is_proc}`
3.  **Mappings**: `{id, query_id, path, method, params_json, deployed, auth_required}`

---

## 🔒 Security Architecture

| Layer | Implementation |
| :--- | :--- |
| **Admin Access** | `require_admin` dependency checks the `X-API-Key` header against bcrypt-hashed keys. |
| **API Consumer** | Mappings can be set to "Public" (no key) or "Secure" (requires admin key). |
| **Data Layer** | SQL Parameter binding prevents injection. No raw string interpolation is used. |
| **Environment** | CORS is strictly configured to protect the Admin API. |

---

## 💻 Technical Stack

- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic v2.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons.
- **Persistence**: Atomic JSON Storage.
- **Supported DBs**: SQLite, MSSQL, PostgreSQL, MySQL.
