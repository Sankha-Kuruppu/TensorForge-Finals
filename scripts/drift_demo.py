"""End-to-end drift demo without the web server.

normal traffic -> shifted traffic -> drift alert + safe mode -> human review
(simulated with synthetic labels) -> retraining -> champion/challenger -> recovery

Usage: python scripts/drift_demo.py   (writes reports/drift_demo.json)
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobshield.config import ARTIFACTS_DIR, PROCESSED_DIR, REPORTS_DIR  # noqa: E402
from jobshield.features import text_hash  # noqa: E402
from jobshield.monitoring.store import Store  # noqa: E402
from jobshield.service import REGISTRY, JobShield  # noqa: E402


def stream(svc, df, labels, tag):
    caught = missed = model_alone_missed = 0
    decisions = {}
    for text, label in zip(df.text, df.label):
        labels[text_hash(text)] = int(label)
        r = svc.predict(text, channel=f"demo:{tag}")
        decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
        if label == 1:
            # a scam is "missed" only if the user is told it looks fine
            if r["decision"] == "legit":
                missed += 1
            else:
                caught += 1
            # what a plain classifier with no monitoring or review would have said
            if r["prob"] < r["threshold"]:
                model_alone_missed += 1
    status = svc.drift_status()
    phase = {"phase": tag, "posts": len(df), "decisions": decisions,
             "scams": int(df.label.sum()), "scams_missed_silently": missed,
             "scams_flagged_or_reviewed": caught, "scams_missed_by_model_alone": model_alone_missed,
             "drift_level": status["level"], "safe_mode": svc.safe_mode, "model": svc.version,
             "signals": {k: v["value"] for k, v in status.get("signals", {}).items()}}
    print(json.dumps(phase))
    return phase


def main():
    db = ARTIFACTS_DIR / "drift_demo.db"
    db.unlink(missing_ok=True)
    # the demo promotes a challenger; keep the real registry untouched
    registry_backup = REGISTRY.read_text()
    svc = JobShield(store=Store(db), auto_retrain=False)
    start_version = svc.version
    normal = pd.read_csv(PROCESSED_DIR / "live_normal.csv")
    shifted = pd.read_csv(PROCESSED_DIR / "shifted.csv")
    labels, phases = {}, []

    phases.append(stream(svc, normal.iloc[:100], labels, "normal"))
    phases.append(stream(svc, shifted.iloc[:400], labels, "shifted"))
    alerts = svc.store.alerts()

    # human review (simulated with the synthetic ground truth)
    reviewed = 0
    for item in svc.store.review_queue("pending", 1000):
        if item["text_hash"] in labels:
            svc.store.submit_review(item["id"], labels[item["text_hash"]])
            reviewed += 1
    print(f"reviewed {reviewed} posts")

    svc._retrain("drift demo")   # synchronous for the script
    events = svc.store.events()
    phases.append(stream(svc, shifted.iloc[400:600], labels, "shifted_after_retrain"))

    out = {"start_model": start_version, "end_model": svc.version, "reviewed_labels": reviewed,
           "phases": phases, "alerts": alerts, "events": events}
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / "drift_demo.json").write_text(json.dumps(out, indent=2, default=str))
    print("wrote reports/drift_demo.json")
    REGISTRY.write_text(registry_backup)


if __name__ == "__main__":
    main()