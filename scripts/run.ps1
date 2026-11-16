# Production-style run: install deps, build the frontend, serve everything from one port.
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "== Backend setup =="
Set-Location "$RootDir\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"
pip install -q -r requirements.txt

Write-Host "== Frontend build =="
Set-Location "$RootDir\frontend"
npm install
npm run build

Write-Host "== Starting server =="
Set-Location "$RootDir\backend"
$Port = if ($env:PORT) { $env:PORT } else { "8000" }
$HostAddr = if ($env:HOST) { $env:HOST } else { "0.0.0.0" }
uvicorn app.main:app --host $HostAddr --port $Port
