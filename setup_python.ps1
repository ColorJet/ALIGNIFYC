# Setup script for Python environment

Write-Host "=== Setting up Alinify Python Environment ===" -ForegroundColor Green

# Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python not found" -ForegroundColor Red
    exit 1
}

$PYTHON_VERSION = python --version
Write-Host "Using: $PYTHON_VERSION" -ForegroundColor Cyan

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (!(Test-Path "venv")) {
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "=== Python Environment Ready ===" -ForegroundColor Green
Write-Host "To activate: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
