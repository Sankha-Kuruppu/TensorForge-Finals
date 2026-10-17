#!/usr/bin/env bash
# Start the API and the dashboard (used by the Docker image and on Linux/macOS).
set -euo pipefail
cd "$(dirname "$0")/.."
uvicorn jobshield.api:app --host 0.0.0.0 --port 8000 &
API_PID=$!
trap 'kill $API_PID' EXIT
streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
