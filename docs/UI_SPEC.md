# JobShield LK: UI specification

This is everything a frontend needs to talk to the JobShield API. The API is already built and running. The UI only calls it and displays the results.

- **Base URL:** `http://localhost:8000` (start the API with `uvicorn jobshield.api:app --port 8000`)
- **Interactive API docs:** `http://localhost:8000/docs` (try every endpoint in the browser)
- **CORS** is open by default, so a UI on another port (e.g. `localhost:3000`) can call the API directly. To restrict it, set `JOBSHIELD_CORS=http://localhost:3000`.
- All requests and responses are JSON. Errors come back as HTTP 4xx with `{"detail": "..."}`.
- `/predict` takes about 0.1 s. `/demo/stream` with 200 posts takes about 20–40 s, so show a spinner. Retraining runs in the background for about 2 minutes.

The UI needs **4 screens**. A reference implementation exists in `dashboard/app.py` (Streamlit). Copy its behaviour, not its looks.

---

## Screen 1: Check a post (the main user-facing screen)

For job seekers. Mobile-first, big result, simple language.

### Input
| Field | Type | Rules |
|---|---|---|
| Post text | multi-line text area | 10–20,000 characters. English, Sinhala or Singlish. Placeholder: "Paste the job post or message here" |
| Example picker (optional) | dropdown | Fills the text area with a sample post (samples are in `dashboard/app.py`, `EXAMPLES`) |
| "Check post" button | button | Disabled while the request runs |

### Call
`POST /predict`
```json
{ "text": "URGENT VACANCIES in Dubai!!! ... WhatsApp only: 07X-XXXXXXX", "channel": "web" }
```

### Response (fields to use)
| Field | Type | Show it as |
|---|---|---|
| `decision` | `"scam"` \| `"review"` \| `"legit"` | **Main result banner.** scam = red "High risk: likely scam"; review = amber "Could not verify: treat as suspicious"; legit = green "No strong scam signals found". Always show an icon **and** text, never colour alone |
| `advice` | string | Text under the banner (what the user should do) |
| `prob` | float 0–1 | "Scam score", e.g. a meter. The decision line sits at `threshold` |
| `threshold` | float | Marker on the score meter |
| `confidence` | float 0–1 | "Confidence" (small) |
| `flags` | string[] | **"Warning signs found"** list. Map codes to labels (table below) |
| `review_reasons` | string[] | If not empty, show "Sent to a human reviewer because: …" |
| `lang` | `"en"` \| `"si"` \| `"singlish"` \| `"ta"` | Small tag: "Detected language" |
| `is_unknown` | bool | If true: small note "This post looks different from what the model has seen" |
| `drift_level` | `"OK"` \| `"WARN"` \| `"ALERT"` \| `"WARMING_UP"` | Optional small status chip |
| `safe_mode` | bool | If true, show "Extra caution mode is on: new scam tactics detected" |
| `id`, `model_version`, `scores`, `nearest_sim`, `text_redacted` | – | Optional "Details" expander for the demo |

Example response:
```json
{
  "id": 42, "decision": "scam", "prob": 0.9948, "threshold": 0.5621, "confidence": 0.9881,
  "flags": ["upfront_fee", "no_checks", "chat_app_only", "urgency"],
  "review_reasons": [], "lang": "en", "is_unknown": false, "nearest_sim": 0.93,
  "advice": "High risk of recruitment fraud. Do not pay any fee or send your passport. Check the agency licence on the SLBFE website or call the SLBFE 1989 hotline.",
  "scores": {"tfidf": 0.99, "embedding": 0.99}, "model_version": "v1",
  "drift_level": "OK", "safe_mode": false,
  "text_redacted": "URGENT VACANCIES in Dubai!!! ... WhatsApp only: PHONE", "text_hash": "ab12...", "channel": "web"
}
```

### Warning-sign labels (`flags`)
| Code | Label |
|---|---|
| `upfront_fee` | Asks for an upfront fee or deposit |
| `guaranteed_visa` | Promises a guaranteed visa |
| `no_checks` | No experience, interview or qualifications needed |
| `chat_app_only` | Contact only through a chat app |
| `urgency` | Pressure to act fast |
| `crypto_or_wallet` | Crypto, QR code or mobile-wallet payment |
| `personal_account` | Payment to a personal account |
| `licensed_agency` | Mentions an SLBFE licence (check it is real) |

---

## Screen 2: Monitoring and drift (for the demo and for SLBFE staff)

### Data
- `GET /monitor/status`: poll every 3–5 s
- `GET /monitor/recent?n=300`: for the charts
- `GET /monitor/alerts`: alerts and response events

### `GET /monitor/status` response
While warming up (fewer than 25 predictions):
```json
{ "level": "WARMING_UP", "window": 3, "needed": 25, "model_version": "v1", "safe_mode": false }
```
Normally:
```json
{
  "level": "ALERT", "window": 50, "model_version": "v1", "safe_mode": true, "retraining": false,
  "signals": {
    "centroid_dist":   {"value": 0.0188, "limit": 0.0041, "baseline": 0.0021, "fired": true},
    "confidence_mean": {"value": 0.6404, "limit": 0.6871, "baseline": 0.7981, "fired": true},
    "unknown_rate":    {"value": 0.70,   "limit": 0.10,   "baseline": 0.03,   "fired": true}
  },
  "lang_mix": {"en": 0.2, "si": 0.36, "singlish": 0.44},
  "scam_rate": 0.31, "review_rate": 0.62
}
```

### Display
| Element | Source | Notes |
|---|---|---|
| **Big status badge** | `level` | OK = green, WARN = amber, ALERT = red, WARMING_UP = grey "Collecting traffic: window/needed". Icon + word |
| Safe mode chip | `safe_mode` | "Safe mode ON" when true |
| Retraining indicator | `retraining` | Spinner "Retraining challenger model…" when true |
| **3 signal cards** | `signals.*` | Title: centroid_dist = "Input distribution shift", confidence_mean = "Mean confidence", unknown_rate = "Unknown-input share". Show `value`, the `limit`, the difference from `baseline`, and FIRED / within limit. Note: confidence fires when **below** its limit; the other two when **above** |
| Scam rate, review rate | `scam_rate`, `review_rate` | Percentages |
| Language mix | `lang_mix` | Small bar or text |
| **Chart 1:** rolling confidence | `/monitor/recent` → `confidence` | Sort by `id`, 20-post rolling mean, one line |
| **Chart 2:** rolling similarity to training data | `/monitor/recent` → `nearest_sim` | Same, separate chart (do not put both on one axis) |
| Alerts table | `/monitor/alerts` → `alerts[]` | Columns: `ts`, `level`, `message`, `model_version` |
| Response events table | `/monitor/alerts` → `events[]` | Columns: `ts`, `kind`, `detail` (`detail` is a JSON string, parse it). Kinds: `safe_mode_on`, `safe_mode_off`, `retrain_started`, `champion_challenger`, `retrain_failed`, `retrain_skipped`. For `champion_challenger` show "Challenger X: test F1 a → b, new-scam F1 c → d, promoted yes/no" |

`GET /monitor/recent?n=300` returns a list, newest first:
```json
[{ "id": 42, "ts": "2026-10-17T05:01:02+00:00", "text_redacted": "...", "text_hash": "ab12...", "lang": "en",
   "prob": 0.99, "decision": "scam", "confidence": 0.98, "nearest_sim": 0.93, "is_unknown": 0,
   "flags": "[\"upfront_fee\"]", "model_version": "v1", "channel": "web" }]
```
(`flags` here is a JSON string; `is_unknown` is 0 or 1.)

### Demo control buttons (same screen)
| Button | Call | Then |
|---|---|---|
| Stream 60 normal posts | `POST /demo/stream` `{"dataset": "live_normal", "n": 60, "offset": <running offset>}` | Keep an offset counter per dataset, +60 each click |
| Stream 200 shifted posts | `POST /demo/stream` `{"dataset": "shifted", "n": 200, "offset": <running offset>}` | +200 each click (600 posts available) |
| Simulate reviewers | `POST /demo/auto_review` | Response `{"labelled": n, "counts": {...}, "retraining": bool}`. Show a toast "Labelled n posts" |
| Retrain now | `POST /retrain` | 400 if nothing is labelled yet: show the `detail` message |
| Reset demo | `POST /demo/reset` | Clears logs, queue and alerts. Reset the offset counters too |

`/demo/stream` response: `{"streamed": 200, "decisions": {"review": 123, "scam": 43, "legit": 34}, "status": {…same as /monitor/status…}}`

---

## Screen 3: Review queue (for human reviewers, e.g. SLBFE investigators)

### Data
`GET /review/queue?status=pending` (also `labelled`, `used`)
```json
{
  "items": [{ "id": 7, "prediction_id": 42, "ts": "...", "reason": "unfamiliar input, low confidence",
              "status": "pending", "label": null, "text_redacted": "...", "text_hash": "...",
              "prob": 0.44, "lang": "singlish", "flags": "[\"upfront_fee\"]" }],
  "counts": { "pending": 141, "labelled": 0, "used": 0 }
}
```

### Display
- Counters: Pending, Labelled, Used in retraining (`counts`; a missing key means 0)
- Note: "Retraining starts automatically during a drift alert once 250 posts are labelled"
- A list of cards (show about 15 at a time). Each card shows `text_redacted` (keep the line breaks), `prob`, `lang`, `reason` and the warning signs (parse `flags`)
- Two buttons per card: **Scam** → `POST /review/{id}` `{"label": 1}`; **Legit** → `POST /review/{id}` `{"label": 0}`. Remove the card on success.

---

## Screen 4: Model

### Data
`GET /model`
```json
{
  "version": "v1", "threshold": 0.5621, "trained_at": "...", "train_rows": 13633, "reviewed_rows": 0,
  "retraining": false,
  "test": { "tfidf": {...}, "embedding": {...}, "ensemble": {
      "all": {"n": 3030, "scams": 325, "precision": 0.93, "recall": 0.91, "f1": 0.92, "pr_auc": 0.96, "tp": 296, "fp": 21, "fn": 29, "tn": 2684},
      "emscad": {...}, "synthetic_sl_current": {...} } },
  "shifted_holdout": { ...same shape... },
  "registry": { "champion": "v1", "history": [{"version": "v1", "promoted_at": "...", "reason": "initial training"}] }
}
```

### Display
- Serving model `version`, `trained_at`, `train_rows`, `reviewed_rows`
- Metrics table: rows = split (`test`, `shifted_holdout`) × model (`tfidf`, `embedding`, `ensemble`) × data source. Columns: n, scams, precision, recall, F1, PR-AUC
- Registry history table: version, promoted_at, reason

---

## Other endpoints
| Method | Path | Use |
|---|---|---|
| GET | `/health` | `{"status": "ok", "model_version": "v1"}`. Show "API offline" if this fails |

## Design notes
- All demo posts are synthetic. Show a small footer: "All examples are synthetic. No real phone numbers, agencies or people."
- Sinhala text must render: use a font with Sinhala support (e.g. Noto Sans Sinhala).
- Never use colour alone for a decision or status. Always include an icon and a word.
