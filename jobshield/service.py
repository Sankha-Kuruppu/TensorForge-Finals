"""JobShield core service: prediction, logging, drift checks and the response loop.

Response to drift (no silent failure):
  1. Safe fallback  - uncertain or unfamiliar posts get a cautious warning
                      instead of a confident "looks fine".
  2. Human review   - those posts go into a review queue.
  3. Alert          - when two or more drift signals fire, an ALERT is logged and
                      the service switches to safe mode (wider review band).
  4. Retraining     - once enough reviewed labels exist during an alert, a
                      challenger model is trained and promoted only if it beats
                      the champion on the shifted holdout without getting worse
                      on the original test set.
"""
import json
import logging
import random
import threading

import joblib
import numpy as np
import pandas as pd

from jobshield.config import ARTIFACTS_DIR, MODELS_DIR
from jobshield.features import detect_lang, normalize, red_flags, redact, text_hash
from jobshield.models import confidence, embed
from jobshield.monitoring.drift import window_signals
from jobshield.monitoring.store import Store, now

REGISTRY = MODELS_DIR / "registry.json"
WINDOW = 50
REVIEW_BAND = 0.25          # confidence below this goes to human review
SAFE_MODE_REVIEW_BAND = 0.5
# too few labels teach the wrong lesson (tested: ~100 labels made the model distrust
# genuine SLBFE-licensed Sinhala posts); ~250-300 labels learn the new tactic safely
MIN_REVIEWS_TO_RETRAIN = 250
RETRY_EXTRA_LABELS = 100    # after a rejected challenger, wait for this many new labels
AUDIT_RATE = 0.3            # share of confident answers also reviewed during an alert
MAX_TEST_F1_DROP = 0.02

log = logging.getLogger("jobshield")

ADVICE = {
    "scam": "High risk of recruitment fraud. Do not pay any fee or send your passport. "
            "Check the agency licence on the SLBFE website or call the SLBFE 1989 hotline.",
    "review": "We could not verify this post. Treat it as suspicious: never pay before you have a "
              "visa and a contract signed at SLBFE. A reviewer will look at it.",
    "legit": "No strong scam signals found. Still verify the agency licence with SLBFE before paying anything.",
}


def read_registry() -> dict:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return {"champion": None, "history": []}


def promote(version: str, reason: str) -> None:
    reg = read_registry()
    reg["champion"] = version
    reg["history"].append({"version": version, "promoted_at": now(), "reason": reason})
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2))


class JobShield:
    def __init__(self, store: Store | None = None, auto_retrain: bool = True):
        self.store = store or Store()
        self.auto_retrain = auto_retrain
        self.safe_mode = False
        self.retraining = False
        self.last_level = "OK"
        self._lock = threading.Lock()
        self._rng = random.Random(0)
        self.last_attempt_labels = 0
        self.load_champion()

    # -- model ------------------------------------------------------------
    def load_champion(self) -> None:
        version = read_registry()["champion"]
        if not version:
            raise RuntimeError("No champion model. Run: python -m jobshield.train --version v1 --promote")
        self.bundle = joblib.load(MODELS_DIR / f"{version}.joblib")
        self.version = version
        log.info("loaded champion model %s", version)

    # -- prediction -------------------------------------------------------
    def predict(self, text: str, channel: str = "api") -> dict:
        norm = normalize(text)
        b = self.bundle
        emb = embed([norm])[0]
        p_tfidf = float(b["tfidf"].predict_proba([norm])[0, 1])
        p_emb = float(b["emb_clf"].predict_proba(emb[None, :])[0, 1])
        prob = (p_tfidf + p_emb) / 2
        thr = b["threshold"]
        conf = float(confidence(prob, thr))
        ref = b["reference"]
        sim = float(ref.nearest_sim(emb)[0])
        unknown = sim < ref.unknown_threshold
        flags = red_flags(text)

        band = SAFE_MODE_REVIEW_BAND if self.safe_mode else REVIEW_BAND
        reasons = []
        if unknown:
            reasons.append("unfamiliar input")
        if conf < band:
            reasons.append("low confidence")
        if self.safe_mode and prob < thr and {"upfront_fee", "crypto_or_wallet"} & set(flags):
            reasons.append("safe mode: payment request")
        decision = "review" if reasons else ("scam" if prob >= thr else "legit")

        rec = {
            "text_hash": text_hash(text), "text_redacted": redact(text), "lang": detect_lang(text),
            "prob": round(prob, 4), "decision": decision, "confidence": round(conf, 4),
            "nearest_sim": round(sim, 4), "is_unknown": bool(unknown), "flags": flags,
            "model_version": self.version, "channel": channel,
        }
        pid = self.store.log_prediction(rec, emb)
        if decision == "review":
            self.store.enqueue_review(pid, ", ".join(reasons))
        elif self.safe_mode and self._rng.random() < AUDIT_RATE:
            # unbiased sample of confident answers, so retraining does not only
            # see the posts the model found hard (selection bias)
            self.store.enqueue_review(pid, "audit sample")
        log.info("prediction id=%s decision=%s prob=%.3f conf=%.2f unknown=%s model=%s",
                 pid, decision, prob, conf, unknown, self.version)

        status = self.check_drift()
        return {**rec, "id": pid, "scores": {"tfidf": round(p_tfidf, 4), "embedding": round(p_emb, 4)},
                "threshold": round(thr, 4), "review_reasons": reasons, "advice": ADVICE[decision],
                "safe_mode": self.safe_mode, "drift_level": status["level"]}

    # -- monitoring -------------------------------------------------------
    def drift_status(self) -> dict:
        rows = [r for r in self.store.recent_predictions(WINDOW, with_emb=True)
                if r["model_version"] == self.version]
        if len(rows) < WINDOW // 2:
            return {"level": "WARMING_UP", "window": len(rows), "needed": WINDOW // 2,
                    "model_version": self.version, "safe_mode": self.safe_mode}
        status = window_signals(rows, self.bundle["reference"])
        return {**status, "model_version": self.version, "safe_mode": self.safe_mode,
                "retraining": self.retraining}

    def check_drift(self) -> dict:
        status = self.drift_status()
        level = status["level"]
        if level in ("WARN", "ALERT") and level != self.last_level:
            fired = [k for k, s in status["signals"].items() if s["fired"]]
            msg = f"{level}: drift signals fired: {', '.join(fired)}"
            self.store.add_alert(level, status["signals"], msg, self.version)
            log.warning(msg)
        if level == "ALERT" and not self.safe_mode:
            self.safe_mode = True
            self.store.add_event("safe_mode_on", {"model_version": self.version})
            log.warning("safe mode ON: wider review band, payment requests always reviewed")
        if level == "OK" and self.safe_mode:
            self.safe_mode = False
            self.store.add_event("safe_mode_off", {"model_version": self.version})
            log.info("safe mode OFF")
        if level != "WARMING_UP":
            self.last_level = level
        if self.auto_retrain and self.safe_mode:
            self.maybe_retrain()
        return status

    # -- retraining -------------------------------------------------------
    def maybe_retrain(self) -> bool:
        n = len(self.store.labelled_reviews())
        needed = max(MIN_REVIEWS_TO_RETRAIN, self.last_attempt_labels + RETRY_EXTRA_LABELS)
        if n >= needed and not self.retraining:
            self.start_retrain(f"drift alert with {n} reviewed labels")
            return True
        return False

    def start_retrain(self, reason: str) -> bool:
        with self._lock:
            if self.retraining:
                return False
            self.retraining = True
        threading.Thread(target=self._retrain, args=(reason,), daemon=True).start()
        return True

    def _retrain(self, reason: str) -> None:
        from jobshield.train import train
        try:
            reviews = self.store.labelled_reviews()
            if not reviews:
                self.store.add_event("retrain_skipped", {"reason": "no labelled reviews"})
                return
            extra = pd.DataFrame({"text": [r["text_redacted"] for r in reviews],
                                  "text_norm": [r["text_redacted"] for r in reviews],
                                  "label": [r["label"] for r in reviews], "lang": [r["lang"] for r in reviews]})
            self.last_attempt_labels = len(extra)
            path = ARTIFACTS_DIR / "reviewed_batch.csv"
            extra.to_csv(path, index=False)
            self.store.add_event("retrain_started", {"reason": reason, "reviewed": len(extra)})
            log.info("retraining challenger with %d reviewed labels (%s)", len(extra), reason)
            challenger = train(extra=str(path))
            decision = self.compare(self.bundle["report"], challenger)
            self.store.add_event("champion_challenger", decision)
            if decision["promote"]:
                promote(challenger["version"], reason)
                self.store.mark_reviews_used([r["id"] for r in reviews])
                self.load_champion()
                self.safe_mode = False
                self.last_level = "OK"
                self.last_attempt_labels = 0
                log.info("promoted %s", challenger["version"])
            else:
                log.warning("challenger rejected: %s", decision)
        except Exception as e:  # keep serving with the champion if retraining fails
            log.exception("retraining failed")
            self.store.add_event("retrain_failed", {"error": str(e)})
        finally:
            self.retraining = False

    @staticmethod
    def compare(champ: dict, chall: dict) -> dict:
        f1 = lambda r, split: r[split]["ensemble"]["all"]["f1"]
        out = {
            "champion": champ["version"], "challenger": chall["version"],
            "test_f1": [f1(champ, "test"), f1(chall, "test")],
            "shifted_holdout_f1": [f1(champ, "shifted_holdout"), f1(chall, "shifted_holdout")],
        }
        better_on_shift = out["shifted_holdout_f1"][1] > out["shifted_holdout_f1"][0]
        no_regression = out["test_f1"][1] >= out["test_f1"][0] - MAX_TEST_F1_DROP
        out["promote"] = bool(better_on_shift and no_regression)
        return out

    def metrics_summary(self) -> dict:
        r = self.bundle["report"]
        return {"version": self.version, "threshold": self.bundle["threshold"],
                "test": r["test"], "shifted_holdout": r["shifted_holdout"],
                "trained_at": r["trained_at"], "train_rows": r["train_rows"],
                "reviewed_rows": r.get("reviewed_rows", 0), "registry": read_registry()}
