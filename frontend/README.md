# JobShield LK — Web Frontend

A modern, responsive, cyber-defense UI built specifically according to [`docs/UI_SPEC.md`](../docs/UI_SPEC.md).

## Features
- **Screen 1: Verify Overseas Job Offer**: Mobile-first checker for job seekers with preset examples (English, Sinhala, Singlish, Legitimate agency, New tactic SLBFE QR impersonation), decision banners, animated score meter with cutoff threshold indicator, confidence display, 8 explainable red-flag badges, and privacy redaction inspection.
- **Screen 2: Monitoring & Drift Radar**: Live telemetry polling (`/monitor/status`), sliding window (50) drift radar, 3 signal cards with 99.5% learned statistical limits (`centroid_dist`, `confidence_mean`, `unknown_rate`), interactive rolling confidence & training similarity charts (Chart.js), drift alerts log, response events table, and live demo streaming controls.
- **Screen 3: Human Review Queue**: Triage queue for SLBFE officers and investigators to classify flagged posts with instant **Scam** / **Legit** review buttons.
- **Screen 4: Model & Registry**: Serving champion metadata, champion/challenger regression gating policy, evaluation metrics table across TF-IDF, Multilingual E5 Small, and Ensemble models, and model promotion history.

## How to Run

### 1. Ensure Backend is Running
From the repository root:
```bash
uvicorn jobshield.api:app --port 8000
```

### 2. Open the UI
You can open `frontend/index.html` directly in any modern web browser, or serve it with any static server:

#### Using Python:
```bash
python -m http.server 3000 --directory frontend
```
Then visit: **`http://localhost:3000`**

#### Using Node `serve` or `npx`:
```bash
npx serve frontend -p 3000
```
