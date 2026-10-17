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


def confidence(prob: np.ndarray, threshold: float) -> np.ndarray:
    """0 = sitting on the decision threshold, 1 = as far from it as possible."""
    prob = np.asarray(prob)
    return np.where(prob >= threshold, (prob - threshold) / (1 - threshold), (threshold - prob) / threshold)


class ReferenceProfile:
    """What normal production traffic looks like. Used by drift monitoring.

    bank_emb : training embeddings, used for the nearest-neighbour "unknown input" test
    ref_emb  : in-domain (Sri Lankan) validation embeddings = expected production traffic
    ref_conf : model confidence on those validation inputs
    Window limits come from bootstrapping windows of normal traffic, so an alert
    means "this window is less normal than 99.5% of normal windows".
    """

    def __init__(self, bank_emb, ref_emb, ref_conf, window: int = 50, max_bank: int = 8000):
        rng = np.random.default_rng(SEED)
        idx = rng.choice(len(bank_emb), size=min(max_bank, len(bank_emb)), replace=False)
        self.bank = bank_emb[idx].astype(np.float32)
        self.window = window
        self.centroid = ref_emb.mean(axis=0)
        ref_sim = self.nearest_sim(ref_emb)
        self.unknown_threshold = float(np.quantile(ref_sim, 0.02))
        unknown = ref_sim < self.unknown_threshold

        stats = {"centroid_dist": [], "confidence_mean": [], "unknown_rate": []}
        for _ in range(1000):
            w = rng.choice(len(ref_emb), size=window, replace=True)
            stats["centroid_dist"].append(self.centroid_dist(ref_emb[w]))
            stats["confidence_mean"].append(float(ref_conf[w].mean()))
            stats["unknown_rate"].append(float(unknown[w].mean()))
        self.baseline = {k: float(np.mean(v)) for k, v in stats.items()}
        self.limits = {
            "centroid_dist": float(np.quantile(stats["centroid_dist"], 0.995)) * 1.25,
            "confidence_mean": float(np.quantile(stats["confidence_mean"], 0.005)) * 0.9,
            "unknown_rate": max(float(np.quantile(stats["unknown_rate"], 0.995)), 0.10),
        }

    @staticmethod
    def _cos(a, b):
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    def nearest_sim(self, emb: np.ndarray) -> np.ndarray:
        return (np.atleast_2d(emb).astype(np.float32) @ self.bank.T).max(axis=1)

    def centroid_dist(self, emb: np.ndarray) -> float:
        return float(1 - self._cos(np.atleast_2d(emb).mean(axis=0), self.centroid))
