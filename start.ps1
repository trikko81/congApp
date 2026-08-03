# PowerShell Start Script for CongApp
Write-Host "🚀 Cleaning up any stale processes on ports 3000 & 8001..." -ForegroundColor Yellow

Get-NetTCPConnection -LocalPort 3000, 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {
    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
}

Write-Host "🚀 Launching CongApp Backend & Frontend..." -ForegroundColor Green

$rootDir = $PSScriptRoot

$pythonExe = "$rootDir\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn backend.main:app --reload --port 8001" -WorkingDirectory $rootDir
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev --prefix frontend" -WorkingDirectory $rootDir

Write-Host "✅ Backend (FastAPI) running on http://localhost:8001" -ForegroundColor Cyan
Write-Host "✅ Frontend (Next.js) running on http://localhost:3000" -ForegroundColor Cyan
