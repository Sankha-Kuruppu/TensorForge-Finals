"""Drift signals computed over a sliding window of recent predictions.

Three signals, each compared with limits learnt from normal traffic:
  centroid_dist   - input distribution shift: the window's mean embedding moves
                    away from the reference centroid
  confidence_mean - falling confidence: the model is less sure than usual
  unknown_rate    - share of inputs unlike anything in the training data
"""
import numpy as np

from jobshield.models import ReferenceProfile


def window_signals(rows: list[dict], ref: ReferenceProfile) -> dict:
    emb = np.vstack([r["emb"] for r in rows])
    values = {
        "centroid_dist": ref.centroid_dist(emb),
        "confidence_mean": float(np.mean([r["confidence"] for r in rows])),
        "unknown_rate": float(np.mean([r["is_unknown"] for r in rows])),
    }
    fired = {
        "centroid_dist": values["centroid_dist"] > ref.limits["centroid_dist"],
        "confidence_mean": values["confidence_mean"] < ref.limits["confidence_mean"],
        "unknown_rate": values["unknown_rate"] > ref.limits["unknown_rate"],
    }
    n_fired = sum(fired.values())
    level = "ALERT" if n_fired >= 2 else "WARN" if n_fired == 1 else "OK"
    return {
        "level": level,
        "window": len(rows),
        "signals": {k: {"value": round(values[k], 4), "limit": round(ref.limits[k], 4),
                        "baseline": round(ref.baseline[k], 4), "fired": bool(fired[k])}
                    for k in values},
        "lang_mix": _share([r["lang"] for r in rows]),
        "scam_rate": round(float(np.mean([r["decision"] == "scam" for r in rows])), 3),
        "review_rate": round(float(np.mean([r["decision"] == "review" for r in rows])), 3),
    }


def _share(values) -> dict:
    vals, counts = np.unique(values, return_counts=True)
    return {str(v): round(c / len(values), 3) for v, c in zip(vals, counts)}
