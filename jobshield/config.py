from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
REPORTS_DIR = ROOT / "reports"
LOG_DB = ARTIFACTS_DIR / "predictions.db"

EMSCAD_URL = (
    "https://huggingface.co/datasets/victor/real-or-fake-fake-jobposting-prediction"
    "/resolve/main/fake_job_postings.csv"
)
EMSCAD_FILE = RAW_DIR / "fake_job_postings.csv"

EMBED_MODEL = "intfloat/multilingual-e5-small"
EMBED_MAX_TOKENS = 256

SEED = 42
