<#
Initialize the development environment:
- Create a virtual environment (.venv)
- Install backend dependencies (requirements.txt)
- Install MSSQL drivers (pyodbc, pymssql)

Usage (PowerShell):
  .\init_env.ps1
#>

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "--- 🛠 Strict Environment Initialization ---" -ForegroundColor Cyan

# 1. Create venv if missing
if (-not (Test-Path ".venv")) {
    Write-Host "Creating local virtual environment (.venv)..."
    python -m venv .venv
}

# 2. DEFINITIVE path to local venv python
# This ensures we NEVER touch the global python/pip
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "CRITICAL: Could not create or find the local virtual environment at .venv"
    exit 1
}

Write-Host "Using VENV Python: $python" -ForegroundColor Gray

# 3. Upgrade PIP inside the venv
Write-Host "Upgrading local pip..."
& $python -m pip install --upgrade pip --quiet

# 4. Install requirements ONLY into venv
$reqFile = Join-Path $root "setup/requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "Installing dependencies from $reqFile (using binaries)..."
    # --prefer-binary speed up installation for packages like pyodbc/psycopg2
    & $python -m pip install -r $reqFile --quiet --prefer-binary
} else {
    Write-Warning "requirements.txt not found. Installing core dependencies manually..."
    & $python -m pip install fastapi "uvicorn[standard]" pydantic SQLAlchemy bcrypt pyodbc pymssql --quiet --prefer-binary
}

# 5. Note: MSSQL drivers are already in requirements.txt

# 6. Install Frontend dependencies (Only if dist is missing)
$distDir = Join-Path $root "frontend/dist"
if (-not (Test-Path $distDir)) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "`nPre-built frontend not found. Installing Node dependencies..." -ForegroundColor Cyan
        $frontDir = Join-Path $root "frontend"
        Push-Location $frontDir
        & npm install --no-audit --no-fund --quiet
        Pop-Location
    } else {
        Write-Host "`nNode.js/NPM not detected. Skipping Frontend installation." -ForegroundColor Yellow
    }
} else {
    Write-Host "`n✅ Pre-built frontend detected. Skipping npm install to save time." -ForegroundColor Gray
}

Write-Host "`n✅ SUCCESS: All dependencies are contained within the project folder." -ForegroundColor Green
Write-Host "You can now run: .\run_ui.ps1"
