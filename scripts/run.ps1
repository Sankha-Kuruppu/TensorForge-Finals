# Windows: set up, build data, train and start the API + dashboard.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\run.ps1 [-SkipTrain]
param([switch]$SkipTrain)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"

python -m pip install -r requirements.txt
if (-not $SkipTrain) {
    python -m jobshield.data.prepare
    python -m jobshield.train --version v1 --promote
}
Start-Process python -ArgumentList "-m", "uvicorn", "jobshield.api:app", "--port", "8000" -NoNewWindow
python -m streamlit run dashboard/app.py --server.port 8501
