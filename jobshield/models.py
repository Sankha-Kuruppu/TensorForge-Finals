"""Model components: TF-IDF baseline, multilingual embedding classifier, ensemble."""
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from jobshield.config import EMBED_MAX_TOKENS, EMBED_MODEL, SEED


def build_tfidf() -> Pipeline:
    # char_wb n-grams handle Sinhala script and inconsistent Singlish spelling;
    # word n-grams capture phrases like "registration fee".
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=100_000,
                                 sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3,
                                 max_features=150_000, sublinear_tf=True)),
    ])
    clf = LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, random_state=SEED)
    return Pipeline([("features", features), ("clf", clf)])


@lru_cache(maxsize=1)
def get_encoder():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL, device="cpu")
    model.max_seq_length = EMBED_MAX_TOKENS
    return model


def embed(texts, batch_size: int = 64, show_progress: bool = False) -> np.ndarray:
    # e5 models expect a "query: " prefix for classification-style use
    texts = [f"query: {t}" for t in texts]
    return get_encoder().encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                show_progress_bar=show_progress, convert_to_numpy=True)


def build_embedding_clf() -> LogisticRegression:
    return LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000, random_state=SEED)


class ReferenceProfile:
    """What 'normal' inputs look like at training time. Used by drift monitoring."""

    def __init__(self, train_emb: np.ndarray, val_emb: np.ndarray, val_conf: np.ndarray,
                 max_ref: int = 6000):
        rng = np.random.default_rng(SEED)
        idx = rng.choice(len(train_emb), size=min(max_ref, len(train_emb)), replace=False)
        self.bank = train_emb[idx].astype(np.float32)
        self.centroid = train_emb.mean(axis=0)
        val_sim = self.nearest_sim(val_emb)
        # an input is "unknown" if it is less similar to training data than 99% of val inputs
        self.unknown_threshold = float(np.quantile(val_sim, 0.01))
        self.val_unknown_rate = float((val_sim < self.unknown_threshold).mean())
        self.val_conf_mean = float(val_conf.mean())
        self.val_centroid_dist = float(1 - self._cos(val_emb.mean(axis=0), self.centroid))

    @staticmethod
    def _cos(a, b):
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    def nearest_sim(self, emb: np.ndarray) -> np.ndarray:
        return (emb.astype(np.float32) @ self.bank.T).max(axis=1)

    def centroid_dist(self, emb: np.ndarray) -> float:
        return float(1 - self._cos(emb.mean(axis=0), self.centroid))
