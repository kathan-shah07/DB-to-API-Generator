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

## 🛠 Component Breakdown

### 1. Management API (Core Engine)
Built with **FastAPI**, the core engine is responsible for:
- **Lifecycle Management**: Start-up logic that reads saved mappings from storage and registers them as live routes.
- **Dynamic Route Registry**: Utilizing FastAPI's `app.add_api_route`, the system can add or remove routes at runtime without a server restart.
- **Validation Wrapper**: For every dynamic route, a custom Pydantic model is built on-the-fly (`param_model.py`) to validate incoming JSON bodies or query parameters.

### 2. Persistence Layer (`storage.py`)
Instead of requiring a separate heavy database, we use an **Atomic JSON Storage** system:
- **Metadata Directory**: Stores `connectors.json`, `queries.json`, `mappings.json`, and `api_keys.json`.
- **Atomic Writes**: Uses a "Write-Rename" pattern (writing to `.tmp` then replacing) to prevent data corruption.
- **In-Memory Cache**: Critical configuration is loaded into the app state at startup for high-performance routing.

### 3. SQL Engine & Adapter (`db_adapter.py` & `exec_query.py`)
Multi-database support is handled via **SQLAlchemy**:
- **Connection Pooling**: Each connector maintains its own engine/pool.
- **Safe Binding**: All parameters are passed as bound variables to the SQLAlchemy `text()` construct, providing native protection against SQL Injection.
- **Auto-Discovery**: Uses SQLAlchemy `inspect` to extract table schemas and sample rows.

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

## � Security Architecture

| Layer | Implementation |
| :--- | :--- |
| **Admin Access** | `require_admin` dependency checks the `X-API-Key` header against bcrypt-hashed keys. |
| **API Consumer** | Mappings can be set to "Public" (no key) or "Secure" (requires admin key). |
| **Data Layer** | SQL Parameter binding prevents injection. No raw string interpolation is used. |
| **Environment** | CORS is strictly configured to protect the Admin API. |

---

## 💻 Technical Stack

- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic v2.
- **Frontend**: React 18, Vite.
- **Persistence**: Atomic JSON Storage.
- **Supported DBs**: SQLite, MSSQL, PostgreSQL, MySQL.
