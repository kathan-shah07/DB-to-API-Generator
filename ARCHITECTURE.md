# 🏗 System Architecture: DB-to-API Generator

This document outlines the architectural design, component interaction, and data flow of the DB-to-API Generator.

---

## 🛰 System Overview

The DB-to-API Generator is a low-code platform that transforms raw database connections into secure, validated RESTful APIs. It follows a **Decoupled Architecture** with an asynchronous backend and a modern single-page application (SPA) frontend.

---

## 📊 High-Level Flow

```text
   +=========================================+
   |             CLIENT LAYER                |
   |      (Browser / Postman / Terminal)     |
   +====================+====================+
                        |
            (A) ADMIN   |   (B) LIVE ENDPOINT
               FLOW     |        API FLOW
                        |
    +-------------------v-------------------+
    |           FASTAPI ENGINE              |
    |  (main.py / Dynamic Route Registry)   |
    +---------+-------------------+---------+
              |                   |
      +-------v-------+   +-------v-------+
      | ADMIN HANDLER |   | DYNAMIC ROUTE |
      +-------+-------+   +-------+-------+
              |                   |
      +-------v-------+   +-------v-------+
      | STORAGE (JSON)|   |  SQL EXECUTOR |
      +---------------+   +-------+-------+
                                  | (SQLAlchemy)
               +------------------+------------------+
               |                  |                  |
               v                  v                  v
        [ MS SQL Server ]   [ PostgreSQL ]     [ SQLite/MySQL ]
```

---

## 🧩 Core Components

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
