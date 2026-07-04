# Backend Startup Script
Write-Host "Starting Backend Server..." -ForegroundColor Green
cd backend

# Create venv with Python 3.12 if missing
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Creating Python 3.12 virtual environment..." -ForegroundColor Yellow
    py -3.12 -m venv venv
    & .\venv\Scripts\pip.exe install -r requirements.txt
}

$python = ".\venv\Scripts\python.exe"

# Ensure words.txt exists before starting the server
if (-not (Test-Path "words.txt") -and (Test-Path "google-10k-common.txt")) {
    Write-Host "Creating words.txt from google-10k-common.txt..." -ForegroundColor Yellow
    Copy-Item "google-10k-common.txt" "words.txt"
}

$env:PORT = "8000"
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Cyan
& $python main.py
Write-Host "Backend server stopped." -ForegroundColor Red
pause

