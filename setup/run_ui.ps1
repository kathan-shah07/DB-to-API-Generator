<#
Run the UI locally with a temporary metadata directory and an admin API key.

Usage (PowerShell):
  .\run_ui.ps1
  .\run_ui.ps1 -Port 8000
  .\run_ui.ps1 -MetadataDir C:\temp\mydbapi_meta

What this script does:
- Creates a metadata directory (or uses the provided one) and sets $env:METADATA_DIR
- Runs scripts/create_admin_key.py with the repository python (prefer .venv) and prints the plaintext token
- Starts uvicorn in a new process using the same python executable
- Opens the default browser to the UI URL

Notes:
- Prefer running this from a PowerShell session with the repo root as current directory.
- If you have a virtualenv at .venv, the script will use .\.venv\Scripts\python.exe. Otherwise it uses `python` from PATH.
- To stop the server, use Stop-Process -Id <PID> (PID is printed by this script).
#>
param(
    [int]$Port = 8000,
    [string]$HostAddr = '0.0.0.0',
    [string]$MetadataDir = ''
)

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $MetadataDir -or $MetadataDir -eq '') {
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $MetadataDir = Join-Path $root ("metadata_run_$ts")
}

if (-not (Test-Path $MetadataDir)) { New-Item -ItemType Directory -Force -Path $MetadataDir | Out-Null }
Write-Host "Using METADATA_DIR: $MetadataDir"
$env:METADATA_DIR = $MetadataDir

# choose python executable (prefer venv)
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPython) { $python = $venvPython } else { $python = 'python' }

# create admin key
Write-Host "Creating admin API key..."
try {
    $out = & $python (Join-Path $root 'scripts\create_admin_key.py') 2>&1
    $token = $out | Select-Object -Last 1
    if (-not $token) { Write-Warning "No token printed by create_admin_key.py. Output:\n$out" }
    else {
        # copy to clipboard for convenience (PowerShell 5.1+)
        try { Set-Clipboard -Value $token -ErrorAction Stop; Write-Host "(token copied to clipboard)" }
        catch { }
    }
} catch {
    Write-Warning "Failed to run create_admin_key.py: $_"
    $token = ''
}

Write-Host "\nAdmin token (copy & save now):" -ForegroundColor Cyan
Write-Host $token -ForegroundColor Yellow
Write-Host "\nStarting server in DEV_MODE..."

# Start server with DEV_MODE=1 in the environment for the launched process
$psCmd = "`$env:DEV_MODE='1'; & '$python' -m uvicorn backend.main:app --reload --host $HostAddr --port $Port"
$proc = Start-Process -FilePath powershell -ArgumentList '-NoProfile','-NoExit','-Command',$psCmd -WorkingDirectory $root -PassThru
Start-Sleep -Seconds 1

$uiUrl = "http://localhost:$Port"
if ($HostAddr -eq '0.0.0.0') {
    # Find a valid local IP, skipping 169.254.* fallbacks
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1" } | Select-Object -First 1).IPAddress
    if ($ip) {
        Write-Host "`n🌐 Network URL: http://$($ip):$Port" -ForegroundColor Green
    }
}
try { Start-Process $uiUrl } catch { Write-Host "Open your browser to $uiUrl" }

Write-Host "Server started (PID $($proc.Id))."
Write-Host "Paste the admin token into the UI (top-right) and click Save."
Write-Host "To stop the server: Stop-Process -Id $($proc.Id)"
