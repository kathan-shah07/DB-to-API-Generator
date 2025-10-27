DB_API - Minimal admin backend
==============================

Overview
--------
DB_API is a small admin backend (FastAPI) and a collection of helper modules that let you define connectors, queries, and runtime mappings backed by simple atomic JSON metadata files. The project provides both HTTP (FastAPI) endpoints and a headless execution path so tests can run even when FastAPI imports fail in some environments.

This README documents the project purpose, the main files and scripts, how to run the app and tests on Windows PowerShell, configuration (metadata directory), and troubleshooting tips.

Repository layout and file descriptions
-------------------------------------
Top-level files and their purpose:

- `main.py` — FastAPI application exposing admin and runtime endpoints.
- `storage.py` — Atomic JSON helpers used to persist metadata (connectors, queries, mappings, logs). Writes are atomic (tmp -> fsync -> replace).
- `exec_query.py` — Query execution helpers (sqlite-first execution path and helpers to run parameterized queries).
- `param_model.py` — Builds dynamic Pydantic models to validate mapping/param inputs at runtime.
- `sql_utils.py` — SQL helper utilities used by query execution.
- `DB.py`, `dbtest.py`, `discover.py` — assorted DB helpers and discovery/testing utilities used by scripts and tests.
- `metrics.py` — Basic metrics collection utilities.
- `rate_limit.py` — A small rate-limiting helper used by runtime endpoints.
- `errors.py` — Centralized error types and helpers.
- `storage.py` — (see above) metadata storage layer.
- `test_connectors.py` — connector-related tests/helpers.
- `requirements.txt` — pinned Python dependencies required to run and test the project.
- `README.md` — this document.
- `arch.MD` — architecture notes and design rationale (high level).
- `run_ui.ps1` — convenience PowerShell script to run any local UI server (if present).

Scripts and static assets
-------------------------
- `scripts/create_admin_key.py` — helper that creates a one-time admin API token, stores a hash in metadata, and prints the plaintext token (save it securely).
- `scripts/headless_e2e.py` — headless end-to-end runner that exercises core flows without importing FastAPI (useful for environments where FastAPI/Pydantic import-time issues occur).
- `scripts/e2e_test.py` — full HTTP e2e test helper that starts uvicorn and runs the end-to-end flow over HTTP.

Static files (used by the optional UI):
- `static/index.html`, `static/app.js`, `static/style.css` — minimal frontend assets served by the app when used.

Tests
-----
- `tests/test_integration_fastapi.py` — integration test that tries the TestClient (HTTP) path first and falls back to the headless flow if FastAPI/TestClient import fails. This ensures core logic is tested even when the HTTP stack can't be imported in the test environment.

Quick start (Windows PowerShell)
--------------------------------

1) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Run the FastAPI app (development)

```powershell
# run with autoreload
uvicorn main:app --reload
```

Configuration: metadata directory
---------------------------------
By default metadata files are written to a `metadata` directory in the project root. To run with an isolated metadata directory (recommended for tests and CI), set the `METADATA_DIR` environment variable. Example (PowerShell):

```powershell
$env:METADATA_DIR = 'C:\temp\db_api_test_metadata'
```

Create an admin API key (one-time)
---------------------------------
Run the included helper to generate and store an admin API key hash. The script prints the plaintext token once — store it safely.

```powershell
python .\scripts\create_admin_key.py
```

Testing the project
-------------------
Use an isolated `METADATA_DIR` for tests to avoid clobbering development metadata (see above).

Run unit tests and the integration test suite with pytest:

```powershell
pytest -q
```

Run only the integration test (pytest will try HTTP+TestClient then fall back to headless when needed):

```powershell
pytest -q tests/test_integration_fastapi.py
```

If FastAPI or TestClient imports fail in your environment, run the headless e2e runner which does not require the HTTP stack:

```powershell
python .\scripts\headless_e2e.py
```

Full HTTP-driven e2e
--------------------
To exercise the full HTTP path (requires FastAPI + uvicorn import working in your environment):

```powershell
python .\scripts\e2e_test.py
```

Troubleshooting
---------------
- If pytest crashes during import with an error like:

		TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'

	This often indicates a FastAPI / Pydantic version incompatibility or an import-time forward-ref resolution issue. Workarounds:

	1) Use the headless e2e path: `python .\scripts\headless_e2e.py` — this exercises core logic without importing FastAPI.
	2) Create a clean virtual environment and install the pinned `requirements.txt`. If necessary, try different compatible versions of FastAPI/Pydantic.

- If you want to force the headless flow during tests, run the headless script directly or adjust test environment variables to skip the HTTP path.

Notes and next steps
--------------------
- Metadata JSON files are written atomically to avoid partial writes.
- Consider the following improvements for future work:
	- Harden log redaction and secure handling of secrets before production use.
	- Add more unit tests around parameter validation edge cases (lengths, required/optional semantics).
	- Add a small PowerShell wrapper that creates a temporary `METADATA_DIR` and runs the integration test for convenience.

Contributing
------------
Pull requests are welcome. If you add features that change metadata shape, please include migration notes and tests. When editing public APIs, add or update corresponding tests.

License
-------
See repository metadata or add a LICENSE file as needed.

Enjoy exploring the code!
