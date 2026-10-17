#!/usr/bin/env bash
# Linux/macOS: set up, build data, train and start the API + dashboard.
# Usage:  bash scripts/run.sh [--skip-train]
set -euo pipefail
cd "$(dirname "$0")/.."
pip install -r requirements.txt
if [[ "${1:-}" != "--skip-train" ]]; then
  python -m jobshield.data.prepare
  python -m jobshield.train --version v1 --promote
fi
bash scripts/start.sh
