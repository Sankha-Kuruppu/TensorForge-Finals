"""FastAPI service.  Run: uvicorn jobshield.api:app --port 8000"""
import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from jobshield.config import ARTIFACTS_DIR, PROCESSED_DIR
from jobshield.features import text_hash
from jobshield.service import JobShield

(ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(ARTIFACTS_DIR / "logs" / "service.log",
                                                           encoding="utf-8")])

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["svc"] = JobShield()
    state["demo_labels"] = {}
    yield


app = FastAPI(title="JobShield LK", version="1.0",
              description="Fake overseas-job post detection with drift monitoring", lifespan=lifespan)


def svc() -> JobShield:
    return state["svc"]


class PredictIn(BaseModel):
    text: str = Field(..., min_length=10, max_length=20000)
    channel: str = "api"


class ReviewIn(BaseModel):
    label: int = Field(..., ge=0, le=1, description="1 = scam, 0 = legitimate")


class StreamIn(BaseModel):
    dataset: str = Field("live_normal", pattern="^(live_normal|shifted)$")
    n: int = Field(50, ge=1, le=600)
    offset: int = Field(0, ge=0)


@app.get("/health")
def health():
    return {"status": "ok", "model_version": svc().version}


@app.post("/predict")
def predict(body: PredictIn):
    return svc().predict(body.text, body.channel)


@app.get("/monitor/status")
def monitor_status():
    return svc().drift_status()


@app.get("/monitor/recent")
def monitor_recent(n: int = 100):
    return svc().store.recent_predictions(n)


@app.get("/monitor/alerts")
def monitor_alerts():
    return {"alerts": svc().store.alerts(), "events": svc().store.events()}


@app.get("/review/queue")
def review_queue(status: str = "pending"):
    return {"items": svc().store.review_queue(status), "counts": svc().store.review_counts()}


@app.post("/review/{review_id}")
def submit_review(review_id: int, body: ReviewIn):
    svc().store.submit_review(review_id, body.label)
    svc().check_drift()
    return {"ok": True, "counts": svc().store.review_counts()}


@app.post("/retrain")
def retrain():
    if not svc().store.labelled_reviews():
        raise HTTPException(400, "no labelled reviews to learn from")
    started = svc().start_retrain("manual trigger")
    return {"started": started, "retraining": svc().retraining}


@app.get("/model")
def model_info():
    s = svc().metrics_summary()
    s["retraining"] = svc().retraining
    return s


# ---------------------------------------------------------------------------
# Demo helpers: replay synthetic traffic and simulate a human reviewer.
# The simulated reviewer uses the synthetic ground-truth labels.
# ---------------------------------------------------------------------------
@app.post("/demo/stream")
def demo_stream(body: StreamIn):
    df = pd.read_csv(PROCESSED_DIR / f"{body.dataset}.csv").iloc[body.offset: body.offset + body.n]
    decisions = {}
    for text, label in zip(df.text, df.label):
        state["demo_labels"][text_hash(text)] = int(label)
        r = svc().predict(text, channel=f"demo:{body.dataset}")
        decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
    return {"streamed": len(df), "decisions": decisions, "status": svc().drift_status()}


@app.post("/demo/auto_review")
def demo_auto_review(limit: int = 2000):
    done = 0
    for item in svc().store.review_queue("pending", limit):
        label = state["demo_labels"].get(item["text_hash"])
        if label is not None:
            svc().store.submit_review(item["id"], label)
            done += 1
    svc().check_drift()
    return {"labelled": done, "counts": svc().store.review_counts(), "retraining": svc().retraining}


@app.post("/demo/reset")
def demo_reset():
    svc().store.reset()
    svc().safe_mode = False
    svc().last_level = "OK"
    svc().last_attempt_labels = 0
    return {"ok": True}
