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
from jobshield.features import text_hash
from jobshield.models import ReferenceProfile, build_embedding_clf, build_tfidf, confidence, embed

EMB_CACHE = ARTIFACTS_DIR / "embeddings"
REVIEWED_WEIGHT = 5.0


def load_split(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


def cached_embed(name: str, df: pd.DataFrame) -> np.ndarray:
    """Embeddings cached per text (keyed by hash): only new or changed texts are encoded."""
    EMB_CACHE.mkdir(parents=True, exist_ok=True)
    path, key_path = EMB_CACHE / f"{name}.npy", EMB_CACHE / f"{name}.keys.json"
    texts = df.text_norm.tolist()
    keys = [text_hash(t) for t in texts]
    known = {}
    if path.exists() and key_path.exists():
        known = dict(zip(json.loads(key_path.read_text()), np.load(path)))
    missing = [i for i, k in enumerate(keys) if k not in known]
    if missing:
        print(f"embedding {name}: {len(missing)} of {len(texts)} texts not cached...")
        for i, e in zip(missing, embed([texts[i] for i in missing], show_progress=True)):
            known[keys[i]] = e
    emb = np.vstack([known[k] for k in keys])
    np.save(path, emb)
    key_path.write_text(json.dumps(keys))
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
    holdout_df = load_split("shifted_holdout")
    train_emb, val_emb = cached_embed("train", train_df), cached_embed("val", val_df)
    test_emb, shifted_emb = cached_embed("test", test_df), cached_embed("shifted", shifted_df)
    holdout_emb = cached_embed("shifted_holdout", holdout_df)

    extra_df, extra_emb = None, None
    if extra:
        # reviewed production inputs (labelled by human reviewers) become training data
        extra_df = pd.read_csv(extra)
        extra_df["source"] = "reviewed"
        extra_emb = embed(extra_df.text_norm.tolist())
        train_df = pd.concat([train_df, extra_df], ignore_index=True)
        train_emb = np.vstack([train_emb, extra_emb])
        print(f"added {len(extra_df)} reviewed examples")

    # recent human-reviewed labels describe today's tactics, so they count more
    weights = np.where(train_df.source == "reviewed", REVIEWED_WEIGHT, 1.0)
    print("training tfidf...")
    tfidf = build_tfidf().fit(train_df.text_norm, train_df.label, clf__sample_weight=weights)
    print("training embedding classifier...")
    emb_clf = build_embedding_clf().fit(train_emb, train_df.label, sample_weight=weights)

    def predict_all(df, emb):
        pt = tfidf.predict_proba(df.text_norm)[:, 1]
        pe = emb_clf.predict_proba(emb)[:, 1]
        return {"tfidf": pt, "embedding": pe, "ensemble": (pt + pe) / 2}

    val_p = predict_all(val_df, val_emb)
    thrs = {m: best_threshold(val_df.label.values, p) for m, p in val_p.items()}
    # monitoring reference = in-domain (Sri Lankan) validation traffic
    sl_val = (val_df.source == "synthetic_sl_current").values
    ref_emb = val_emb[sl_val]
    ref_conf = confidence(val_p["ensemble"][sl_val], thrs["ensemble"])
    if extra_df is not None:
        # reviewed posts are the "new normal" the monitor should now expect
        ref_emb = np.vstack([ref_emb, extra_emb])
        ref_conf = np.concatenate([ref_conf, confidence(predict_all(extra_df, extra_emb)["ensemble"],
                                                        thrs["ensemble"])])
    reference = ReferenceProfile(train_emb, ref_emb, ref_conf)

    report = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(train_df),
        "reviewed_rows": int((train_df.source == "reviewed").sum()),
        "thresholds": {k: round(v, 4) for k, v in thrs.items()},
        "test": evaluate("test", test_df, predict_all(test_df, test_emb), thrs),
        "shifted": evaluate("shifted", shifted_df, predict_all(shifted_df, shifted_emb), thrs),
        "shifted_holdout": evaluate("shifted_holdout", holdout_df,
                                    predict_all(holdout_df, holdout_emb), thrs),
        "drift_limits": reference.limits,
        "drift_baseline": reference.baseline,
    }

    bundle = {
        "version": version, "tfidf": tfidf, "emb_clf": emb_clf,
        "threshold": thrs["ensemble"], "reference": reference, "report": report,
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
    print("shifted_holdout:", {m: v["all"]["f1"] for m, v in report["shifted_holdout"].items()})
    print("drift limits:", reference.limits)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", help="CSV of reviewed examples (text, text_norm, label)")
    ap.add_argument("--version")
    ap.add_argument("--promote", action="store_true", help="make this model the serving champion")
    args = ap.parse_args()
    rep = train(args.extra, args.version)
    if args.promote:
        from jobshield.service import promote
        promote(rep["version"], "initial training")
        print(f"promoted {rep['version']} to champion")
