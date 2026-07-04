# Combined Startup Script for Fullstack App
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Word Filter Fullstack App" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pythonVersion" -ForegroundColor Green

# Check if Node is available
Write-Host "Checking Node.js..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Node.js is not installed or not in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Node.js: $nodeVersion" -ForegroundColor Green

# Ensure words.txt exists (bootstrap from bundled seed list if missing)
Write-Host "Checking words.txt..." -ForegroundColor Yellow
if (Test-Path "backend\words.txt") {
    Write-Host "words.txt found" -ForegroundColor Green
} elseif (Test-Path "backend\google-10k-common.txt") {
    Write-Host "words.txt not found - creating from google-10k-common.txt..." -ForegroundColor Yellow
    Copy-Item "backend\google-10k-common.txt" "backend\words.txt"
    Write-Host "Created backend\words.txt from seed list" -ForegroundColor Green
} else {
    Write-Host "WARNING: words.txt not found and no seed list available" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting Backend Server on port 8000..." -ForegroundColor Green
Write-Host "Starting Frontend Server on port 4200..." -ForegroundColor Green
Write-Host ""
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend App: http://localhost:4200" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow
Write-Host ""

# Start backend in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; `$env:PORT='8000'; python main.py" -WindowStyle Normal

# Start frontend in a new window  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm start" -WindowStyle Normal

Write-Host "Both servers are starting in separate windows..." -ForegroundColor Green
Write-Host "Check the windows for any errors." -ForegroundColor Yellow

