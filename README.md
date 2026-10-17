# JobShield LK

> Catches fake overseas-job offers today, and notices when recruitment scammers change tactics tomorrow.

**TensorForge 2.0 Final-Forge** · Theme: _Scam-Proof by Design_

## Problem statement

JobShield LK detects fake overseas job offers and illegal recruiter posts in English, Sinhala and Singlish, to protect Sri Lankan migrant workers and their families from recruitment fraud, and flags when scammers change tactics (new destinations, fee tricks or channels) so suspect posts go to human review and retraining instead of slipping through.

## Who we protect

- **People looking for work abroad** who answer "Korea / Israel / Japan / Middle East job" posts on Facebook, TikTok and WhatsApp
- **Their families**, who often borrow or pawn jewellery to pay the "agency fee", "visa fee" or "deposit"
- **First-time job seekers** from rural areas with little way to check whether an agency is licensed

Hundreds of thousands of Sri Lankans leave for foreign employment each year. A single fake offer can cost a family several hundred thousand rupees or more. Posts are written in English, Sinhala or a romanized mix, and they change quickly as scammers move to new destinations and new fee tricks.

## Approach (planned)

| Part           | What it does                                                                                                                 |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Detection      | Text and metadata classifier: TF-IDF baseline and a multilingual sentence-embedding (`intfloat/multilingual-e5-small`) model |
| Service        | FastAPI prediction API plus a Streamlit dashboard                                                                            |
| Logging        | Every prediction is logged to SQLite with redacted text, a hash, the score, confidence and model version                     |
| Drift signals  | Embedding distribution shift, falling confidence, rising share of unknown inputs                                             |
| Drift response | Safe fallback warning, human-review queue, and a retraining trigger with champion/challenger promotion                       |

## Data

No real personal data is used, in line with Sri Lanka's PDPA No. 9 of 2022. Phone numbers, links, agency names and people in the Sri Lankan posts are placeholders.

| Source                                                                                                                                                                      | Licence / method                                                        |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| EMSCAD (Employment Scam Aegean Dataset), 17,880 job ads with 866 fraudulent, University of the Aegean; Hugging Face mirror `victor/real-or-fake-fake-jobposting-prediction` | CC0-1.0                                                                 |
| Sri Lankan overseas-job posts (English, Sinhala, Singlish)                                                                                                                  | Written by the team and expanded with a template generator in this repo |

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
