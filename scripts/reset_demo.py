"""Reset to a clean demo state: champion back to v1, prediction logs cleared.

Usage (stop the API first, start it again afterwards):
  python scripts/reset_demo.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobshield.monitoring.store import Store  # noqa: E402
from jobshield.service import REGISTRY, read_registry  # noqa: E402

reg = read_registry()
first = next(h for h in reg["history"] if h["version"] == "v1")
REGISTRY.write_text(json.dumps({"champion": "v1", "history": [first]}, indent=2))
Store().reset()
print("champion = v1, prediction log, review queue and alerts cleared")
