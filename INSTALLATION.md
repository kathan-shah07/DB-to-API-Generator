# 🛠 Installation Guide: DB-to-API Generator

Follow these steps to set up the DB-to-API Generator on your local machine.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
1.  **Python 3.11+**: [Download here](https://www.python.org/downloads/)
2.  **Node.js & npm**: [Download here](https://nodejs.org/) (Required only if you want to modify the frontend)
3.  **ODBC Drivers** (For MSSQL only): [Download ODBC Driver 17 for SQL Server](https://www.microsoft.com/en-us/download/details.aspx?id=56567)

---

## 🚀 Fast Track Setup (Windows)

If you are on Windows, we provide a one-click setup environment:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-repo/DB-to-API-Generator.git
    cd DB-to-API-Generator
    ```

2.  **Initialize Environment**:
    Run the following command in PowerShell to create a virtual environment and install dependencies:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\init_env.ps1
    ```

3.  **Launch the Application**:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\run_ui.ps1
    ```

---

## 🛠 Manual Installation (All Platforms)

### 1. Backend Setup
1.  **Create a Virtual Environment**:
    ```bash
    python -m venv .venv
    ```
2.  **Activate the Environment**:
    *   **Windows**: `.venv\Scripts\activate`
    *   **macOS/Linux**: `source .venv/bin/activate`
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 2. Frontend Setup (Optional)
The project comes with a pre-built frontend in `frontend/dist`. If you want to rebuild it:
1.  Navigate to the frontend folder:
    ```bash
    cd frontend
    ```
2.  Install packages:
    ```bash
    npm install
    ```
3.  Build the production bundle:
    ```bash
    npm run build
    ```

---

## 🚦 How to Run

1.  **Start the Backend & UI**:
    From the root directory, run:
    ```bash
    python main.py
    ```
2.  **Access the Dashboard**:
    Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

3.  **Authentication**:
    Upon startup, the console will print an `ADMIN_TOKEN`. 
    - Copy this token.
    - Paste it into the "Admin Key" field in the top-right of the web UI.
    - Click **Save**.

---

## 📁 Project Structure
- `main.py`: The FastAPI backend server and API engine.
- `storage.py`: Handles persistence of connectors, queries, and mappings (JSON-based).
- `frontend/`: React source code (Vite + Tailwind).
- `requirements.txt`: Python package dependencies.
- `run_ui.ps1`: Automated start-up script for Windows.
