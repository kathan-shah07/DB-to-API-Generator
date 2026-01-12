# 🛠 Installation Guide: DB-to-API Generator

Follow these steps to set up the DB-to-API Generator on your local machine.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
1.  **Python 3.11+**: [Download here](https://www.python.org/downloads/)
2.  **Node.js & npm**: [Download here](https://nodejs.org/) (Required only for frontend development)
3.  **ODBC Drivers** (For MSSQL only): [Download ODBC Driver 17 for SQL Server](https://www.microsoft.com/en-us/download/details.aspx?id=56567)

---

## 🚀 Fast Track Setup (Windows)

If you are on Windows, we provide automated scripts for environment setup:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/kathan-shah07/DB-to-API-Generator.git
    cd DB-to-API-Generator
    ```

2.  **Initialize Environment**:
    Run the following command in PowerShell to create a virtual environment and install dependencies:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\setup\init_env.ps1
    ```

3.  **Launch the Application**:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\setup\run_ui.ps1
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
    pip install -r setup/requirements.txt
    ```

### 2. Frontend Setup (Optional)
The project comes with a pre-built frontend in `frontend/dist`. To modify/rebuild:
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

1.  **Start the Server**:
    From the root directory, activate your venv and run:
    ```bash
    python backend/main.py
    ```
2.  **Access the Dashboard**:
    Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

3.  **Authentication**:
    Upon the first run, the console will print an **ADMIN TOKEN**.
    - Copy this token.
    - Paste it into the "Admin Key" field in the top-right of the web UI.
    - Click **Save**.

---

## 📁 Project Structure
- `backend/`: FastAPI backend server and API engine.
- `frontend/`: React source code (Vite).
- `setup/`: Installation scripts and requirements.
- `scripts/`: Helper scripts for testing and maintenance.
- `demo/`: Documentation and Postman collections for quick testing.
