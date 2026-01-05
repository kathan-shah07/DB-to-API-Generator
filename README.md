# 🚀 DB-to-API Generator

**Transform your raw databases into secure, documented, and validated REST APIs in seconds.**

DB-to-API Generator is a low-code platform built with **FastAPI** and **React** that allows developers to connect to multiple database types (MSSQL, PostgreSQL, MySQL, SQLite), define parameterized SQL queries, and deploy them as live HTTP endpoints without writing any backend code.

---

## 📖 Complete Documentation

Explore our specialized guides to get the most out of the platform:

*   [**🛠 Installation Guide**](./INSTALLATION.md) - Step-by-step setup for Windows, macOS, and Linux.
*   [**🏗 System Architecture**](./ARCHITECTURE.md) - Deep dive into how the dynamic route engine and storage layer work.
*   [**🔍 Demo & Walkthrough**](./DEMO_GUIDE.md) - A full tutorial on connecting a database and creating your first API.

---

## ✨ Key Features

- **Multi-DB Support**: Native connectors for **Microsoft SQL Server**, **PostgreSQL**, **MySQL**, and **SQLite**.
- **Dynamic Routing**: Deploy APIs like `/api/user/{id}` where `{id}` is validated and passed directly to your SQL.
- **Smart Parameter Builder**: Auto-detects variables in your SQL and lets you define types (Int, String, Float, Bool) and locations (Path, Query, Body, Header).
- **Security First**: 
  - Integrated **Admin API Key** authentication (Bcrypt hashed).
  - SQL Injection protection via SQLAlchemy parameter binding.
  - Public/Private endpoint toggling.
- **Live Lifecycle**: Deploy, Undeploy, or Delete endpoints in real-time without restarting the server.
- **Atomic Persistence**: Configuration is stored in lightweight, version-control-friendly JSON files.

---

## ⚡ Quick Start (Windows)

1.  **Initialize Environment**:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\init_env.ps1
    ```

2.  **Launch the Dashboard**:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\run_ui.ps1
    ```

3.  **Login**: Copy the `ADMIN_TOKEN` printed in your terminal and paste it into the UI.

---

## 📁 Repository Structure

- `main.py`: The core FastAPI engine and Dynamic Route Registry.
- `storage.py`: Atomic JSON persistence layer.
- `exec_query.py`: Safe SQL execution engine with transaction support.
- `frontend/`: Source code for the modern React management dashboard.
- `sample.db`: A pre-configured SQLite database for immediate testing.

---

## 🧪 Testing

We provide a comprehensive test suite to ensure stability across environments:

```powershell
# Run the integration suite
pytest -q tests/test_integration_fastapi.py

# Run headless E2E (skips HTTP stack if needed)
python .\scripts\headless_e2e.py
```

---

## 📄 License
This project is for protoytpe purpose. See repository metadata for details.

---

*Built with ❤️ for PM / Pre-slaes/ support who hate integrating dfatabsed each time for new integration.*
