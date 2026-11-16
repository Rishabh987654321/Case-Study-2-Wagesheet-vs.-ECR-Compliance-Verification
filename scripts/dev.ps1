# Dev mode: backend with --reload as a background job, frontend dev server (with HMR)
# in the foreground. Vite proxies /api to the backend (see frontend/vite.config.ts).
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Set-Location "$RootDir\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"
pip install -q -r requirements.txt

$backendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    & ".venv\Scripts\Activate.ps1"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} -ArgumentList "$RootDir\backend"

Write-Host "== Backend on http://localhost:8000 (reload), frontend dev server starting =="
Set-Location "$RootDir\frontend"
npm install

try {
    npm run dev
} finally {
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
}
