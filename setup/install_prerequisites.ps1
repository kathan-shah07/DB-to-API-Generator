<#
.SYNOPSIS
    Automated Installer for DB-to-API Generator Prerequisites.
    Installs Python 3.11, Node.js LTS, and ODBC Driver 17 for SQL Server.
#>

Param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

function Write-Header {
    param($Text)
    Write-Host "`n"
    Write-Host "--- $Text ---" -ForegroundColor Cyan
    Write-Host "`n"
}

function Check-And-Install {
    param(
        [string]$Name,
        [string]$WingetId,
        [scriptblock]$CheckLogic
    )

    Write-Host "[*] Checking for $Name..." -ForegroundColor Cyan
    $isInstalled = &$CheckLogic

    if ($isInstalled) {
        Write-Host "[OK] $Name is already installed." -ForegroundColor Green
    } else {
        Write-Host "[!] $Name not found. Attempting installation via winget..." -ForegroundColor Yellow
        try {
            # Ensure winget is available
            if (-not (Get-Command "winget" -ErrorAction SilentlyContinue)) {
                throw "winget is not installed or not in PATH. Please install it from the Microsoft Store (App Installer)."
            }

            Write-Host "[+] Installing $Name ($WingetId)... This may take a few minutes." -ForegroundColor Gray
            winget install --id $WingetId --silent --accept-package-agreements --accept-source-agreements
            Write-Host "[DONE] $Name installation initiated successfully." -ForegroundColor Green
        } catch {
            Write-Host "!!! Failed to install ${Name}: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "Please install it manually from: [See INSTALLATION.md]" -ForegroundColor Gray
        }
    }
}

# --- Execution ---

# Check for Admin Privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERROR] This installer requires Administrator privileges to install system runtimes." -ForegroundColor Red
    Write-Host "Please right-click the file and select 'Run as Administrator'." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit
}

Write-Header "DB-to-API Generator: Pre-requisites Installer"

# 1. Python 3.11
Check-And-Install -Name "Python 3.11" -WingetId "Python.Python.3.11" -CheckLogic {
    (Get-Command python -ErrorAction SilentlyContinue) -and ((python --version) -like "*3.1[1-9]*")
}

# 2. Node.js LTS
Check-And-Install -Name "Node.js" -WingetId "OpenJS.NodeJS.LTS" -CheckLogic {
    Get-Command node -ErrorAction SilentlyContinue
}

# 3. ODBC Driver 17
Check-And-Install -Name "ODBC Driver 17 for SQL Server" -WingetId "Microsoft.ODBCDriver17ForSQLServer" -CheckLogic {
    $path1 = "HKLM:\SOFTWARE\Microsoft\Microsoft ODBC Driver 17 for SQL Server"
    $path2 = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Microsoft ODBC Driver 17 for SQL Server"
    (Test-Path $path1) -or (Test-Path $path2)
}

Write-Header "Finalizing Local Setup"

# 4. Run the local project initialization
$initScript = Join-Path $ProjectRoot "setup\init_env.ps1"
if (Test-Path $initScript) {
    Write-Host "Running local environment initialization ($initScript)..." -ForegroundColor Cyan
    Push-Location $ProjectRoot
    powershell -ExecutionPolicy Bypass -File $initScript
    Pop-Location
} else {
    Write-Host "[WARN] init_env.ps1 not found at $initScript. Skipping local setup." -ForegroundColor Yellow
}

Write-Header "Launching Application"

# 5. Launch the server/UI
$runScript = Join-Path $ProjectRoot "setup\run_ui.ps1"
if (Test-Path $runScript) {
    Write-Host "[*] Launching the server and UI..." -ForegroundColor Cyan
    # We run this in a new window so the installer can finish
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$runScript`"" -WorkingDirectory $ProjectRoot
} else {
    Write-Host "[WARN] run_ui.ps1 not found at $runScript." -ForegroundColor Yellow
}

Write-Host "`n[SUCCESS] Setup process completed!" -ForegroundColor Green
Write-Host "The application is now launching in a new window." -ForegroundColor Gray
Write-Host "You can close this installer window." -ForegroundColor Gray
Read-Host "Press Enter to exit..."
