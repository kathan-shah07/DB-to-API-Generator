<#
Initialize the development environment:
- Create a virtual environment (.venv)
- Install backend dependencies (requirements.txt)
- Install MSSQL drivers (pyodbc, pymssql)

Usage (PowerShell):
  .\init_env.ps1
#>

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
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
if (Test-Path "requirements.txt") {
    Write-Host "Installing requirements.txt into .venv..."
    & $python -m pip install -r requirements.txt --quiet
}

# 5. Install MSSQL drivers into venv
Write-Host "Installing MSSQL drivers into .venv..."
& $python -m pip install pyodbc pymssql --quiet

# 6. Install Frontend dependencies (Project local node_modules)
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "`nDetecting Node.js... Installing Frontend dependencies..." -ForegroundColor Cyan
    $frontDir = Join-Path $root "frontend"
    Push-Location $frontDir
    & npm install --no-audit --no-fund
    Pop-Location
} else {
    Write-Host "`nNode.js/NPM not detected. Skipping Frontend installation." -ForegroundColor Yellow
}

Write-Host "`n✅ SUCCESS: All dependencies are contained within the project folder." -ForegroundColor Green
Write-Host "You can now run: .\run_ui.ps1"
