"""Build train / val / test / shifted splits.

  train, val, test : EMSCAD (stratified 70/15/15) + current-era Sri Lankan posts.
                     Sri Lankan test posts use phrasing never seen in training.
  shifted          : shifted-era Sri Lankan posts, used only for the drift demo.
"""
import pandas as pd
from sklearn.model_selection import train_test_split

from jobshield.config import EMSCAD_FILE, PROCESSED_DIR, SEED
from jobshield.data.download import download
from jobshield.data.sl_generator import generate
from jobshield.features import normalize

EMSCAD_TEXT_COLS = ["title", "location", "salary_range", "company_profile",
                    "description", "requirements", "benefits"]


def load_emscad() -> pd.DataFrame:
    download()
    raw = pd.read_csv(EMSCAD_FILE)
    parts = raw[EMSCAD_TEXT_COLS].fillna("").astype(str)
    text = parts.apply(lambda r: "\n".join(v for v in r if v.strip()), axis=1)
    df = pd.DataFrame({"text": text, "label": raw["fraudulent"].astype(int),
                       "lang": "en", "source": "emscad"})
    df = df[df.text.str.len() > 20].drop_duplicates("text")
    return df


def build() -> dict[str, pd.DataFrame]:
    em = load_emscad()
    em_train, em_rest = train_test_split(em, test_size=0.30, stratify=em.label, random_state=SEED)
    em_val, em_test = train_test_split(em_rest, test_size=0.50, stratify=em_rest.label, random_state=SEED)

    sl_trainval = generate(1600, "current", "train", scam_rate=0.45, seed=SEED)
    sl_train, sl_val = train_test_split(sl_trainval, test_size=0.15, stratify=sl_trainval.label,
                                        random_state=SEED)
    sl_test = generate(400, "current", "test", scam_rate=0.45, seed=SEED + 1)
    shifted = generate(600, "shifted", "all", scam_rate=0.55, seed=SEED + 2)
    # separate shifted posts, used only to evaluate a retrained challenger model
    shifted_holdout = generate(300, "shifted", "all", scam_rate=0.55, seed=SEED + 4)
    shifted_holdout = shifted_holdout[~shifted_holdout.text.isin(shifted.text)]
    # normal live traffic for the demo (today's tactics, seen and unseen phrasing)
    live_normal = generate(300, "current", "all", scam_rate=0.45, seed=SEED + 3)
    # normal traffic used only to calibrate drift limits (never trained or tested on)
    monitor_ref = generate(500, "current", "all", scam_rate=0.45, seed=SEED + 5)
    monitor_ref = monitor_ref[~monitor_ref.text.isin(live_normal.text)]

    splits = {
        "train": pd.concat([em_train, sl_train]),
        "val": pd.concat([em_val, sl_val]),
        "test": pd.concat([em_test, sl_test]),
        "shifted": shifted,
        "shifted_holdout": shifted_holdout,
        "live_normal": live_normal,
        "monitor_ref": monitor_ref,
    }
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in splits.items():
        df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
        df["text_norm"] = df.text.map(normalize)
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
        splits[name] = df
        counts = df.groupby("source").label.agg(["count", "sum"]).rename(columns={"sum": "scams"})
        print(f"\n[{name}] {len(df)} rows\n{counts}")
    return splits


if __name__ == "__main__":
    build()
