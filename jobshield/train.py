"""Train the TF-IDF baseline, the embedding model and the ensemble, then evaluate.

Usage:
  python -m jobshield.train                          # train v1 from processed splits
  python -m jobshield.train --extra reviewed.csv     # retrain with reviewed labels (challenger)
"""
import argparse
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)

from jobshield.config import ARTIFACTS_DIR, MODELS_DIR, PROCESSED_DIR, REPORTS_DIR
from jobshield.models import ReferenceProfile, build_embedding_clf, build_tfidf, embed

EMB_CACHE = ARTIFACTS_DIR / "embeddings"


def load_split(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


def cached_embed(name: str, df: pd.DataFrame) -> np.ndarray:
    EMB_CACHE.mkdir(parents=True, exist_ok=True)
    path = EMB_CACHE / f"{name}.npy"
    if path.exists():
        emb = np.load(path)
        if len(emb) == len(df):
            return emb
    print(f"embedding {name} ({len(df)} texts)...")
    emb = embed(df.text_norm.tolist(), show_progress=True)
    np.save(path, emb)
    return emb


def best_threshold(y, p) -> float:
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / (prec + rec + 1e-9)
    return float(thr[np.argmax(f1[:-1])])


def metrics(y, p, thr) -> dict:
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    out = {"n": int(len(y)), "scams": int(y.sum()),
           "precision": precision_score(y, pred, zero_division=0),
           "recall": recall_score(y, pred, zero_division=0),
           "f1": f1_score(y, pred, zero_division=0),
           "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)}
    if len(set(y)) > 1:
        out["pr_auc"] = average_precision_score(y, p)
        out["roc_auc"] = roc_auc_score(y, p)
    return {k: round(v, 4) if isinstance(v, float) else v for k, v in out.items()}


def evaluate(name, df, probs: dict, thrs: dict) -> dict:
    report = {}
    for model, p in probs.items():
        report[model] = {"all": metrics(df.label.values, p, thrs[model])}
        for src, idx in df.groupby("source").groups.items():
            report[model][src] = metrics(df.label.values[idx], p[idx], thrs[model])
    return report


def train(extra: str | None = None, version: str | None = None) -> dict:
    version = version or datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M%S")
    train_df, val_df = load_split("train"), load_split("val")
    test_df, shifted_df = load_split("test"), load_split("shifted")
    train_emb, val_emb = cached_embed("train", train_df), cached_embed("val", val_df)
    test_emb, shifted_emb = cached_embed("test", test_df), cached_embed("shifted", shifted_df)

    if extra:
        # reviewed production inputs (labelled by human reviewers) become training data
        extra_df = pd.read_csv(extra)
        extra_df["source"] = "reviewed"
        extra_emb = embed(extra_df.text_norm.tolist())
        train_df = pd.concat([train_df, extra_df], ignore_index=True)
        train_emb = np.vstack([train_emb, extra_emb])
        print(f"added {len(extra_df)} reviewed examples")

    print("training tfidf...")
    tfidf = build_tfidf().fit(train_df.text_norm, train_df.label)
    print("training embedding classifier...")
    emb_clf = build_embedding_clf().fit(train_emb, train_df.label)

    def predict_all(df, emb):
        pt = tfidf.predict_proba(df.text_norm)[:, 1]
        pe = emb_clf.predict_proba(emb)[:, 1]
        return {"tfidf": pt, "embedding": pe, "ensemble": (pt + pe) / 2}

    val_p = predict_all(val_df, val_emb)
    thrs = {m: best_threshold(val_df.label.values, p) for m, p in val_p.items()}
    val_conf = np.abs(val_p["ensemble"] - 0.5) * 2

    report = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(train_df),
        "thresholds": {k: round(v, 4) for k, v in thrs.items()},
        "test": evaluate("test", test_df, predict_all(test_df, test_emb), thrs),
        "shifted": evaluate("shifted", shifted_df, predict_all(shifted_df, shifted_emb), thrs),
    }

    bundle = {
        "version": version, "tfidf": tfidf, "emb_clf": emb_clf,
        "threshold": thrs["ensemble"],
        "reference": ReferenceProfile(train_emb, val_emb, val_conf),
        "report": report,
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODELS_DIR / f"{version}.joblib")
    with open(REPORTS_DIR / f"metrics_{version}.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({m: {s: {k: r[k] for k in ("precision", "recall", "f1") if k in r}
                          for s, r in v.items()}
                      for m, v in report["test"].items()}, indent=1))
    print("shifted:", {m: v["all"]["f1"] for m, v in report["shifted"].items()})
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", help="CSV of reviewed examples (text, text_norm, label)")
    ap.add_argument("--version")
    args = ap.parse_args()
    train(args.extra, args.version)
