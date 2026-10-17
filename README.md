# ScamShield LK

> Catches scam messages today, and notices when scammers change tactics tomorrow.

**TensorForge 2.0 Final-Forge** · Theme: *Scam-Proof by Design*

## Problem statement

ScamShield LK detects scam SMS and WhatsApp messages in Sinhala, Tamil, English and mixed Singlish to protect first-time mobile-banking users, pensioners and welfare recipients in Sri Lanka. It also monitors itself for drift, so when scammers switch tactics (for example, impersonating the new SL-UDI digital ID) it raises an alert and routes those messages to human review and retraining instead of failing silently.

## Who we protect

- **First-time mobile-banking users** targeted by fake OTP, account-block and "verify your card" messages
- **Pensioners and elderly users** targeted by lottery, prize and fake-relative messages
- **Welfare (Aswesuma) recipients** targeted by fake "payment pending, pay a fee" messages

These groups get messages in Sinhala, Tamil, English or a romanized mix of them. Most scam filters are built for English only.

## Approach (planned)

| Part | What it does |
|---|---|
| Detection | Character n-gram TF-IDF baseline and multilingual sentence-embedding (`intfloat/multilingual-e5-small`) classifier, combined as an ensemble |
| Service | FastAPI prediction API plus a Streamlit dashboard |
| Logging | Every prediction is logged to SQLite with the text redacted, a hash, the score, confidence and model version |
| Drift signals | Embedding distribution shift, falling confidence, rising share of unknown inputs |
| Drift response | Safe fallback warning, human-review queue, and a retraining trigger with champion/challenger promotion |

## Data

No real personal data is used, in line with Sri Lanka's PDPA No. 9 of 2022. Phone numbers, links and names in synthetic messages are placeholders.

| Source | Licence / method |
|---|---|
| _To be filled in during the build_ | |

Splits: train / validation / **held-out test** / **shifted set** (drift demo). Details to be added.

## How to run

_To be added._

## Evaluation results

_To be added._

## Monitoring and drift response

_To be added._

## Architecture

_Diagram to be added._

## AI tools used

- Claude Code (AI coding assistant) for code scaffolding and drafting documentation. All team members have reviewed the code and can explain it.

## Licence

MIT
