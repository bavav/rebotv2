# moderation/gbm_model.py
"""
GradientBoostingSpamClassifier — HistGBM поверх сжатых TF-IDF + meta.

Пайплайн: TF-IDF (word+char+compact) -> TruncatedSVD -> HistGBM.
На sparse GB обычный тормозит; HistGBM требует dense, поэтому SVD.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

from .normalize import normalize, compact
from .own_model import manual_features

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    is_spam: bool
    confidence: float
    proba: float
    reason: str = "gbm_model"


class GradientBoostingSpamClassifier:
    MIN_POSITIVES = 5
    MIN_TOTAL = 20
    N_SVD = 200

    def __init__(
        self,
        model_dir: str = "./shieldmodel/gbm",
        threshold: float = 0.5,
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold

        self.word_vec: Optional[TfidfVectorizer] = None
        self.char_vec: Optional[TfidfVectorizer] = None
        self.compact_vec: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.clf: Optional[HistGradientBoostingClassifier] = None
        self.n_pos: int = 0
        self.n_total: int = 0

    def _fit_vectorizers(self, texts: Sequence[str]) -> None:
        norm_texts = [normalize(t) for t in texts]
        comp_texts = [compact(t) for t in texts]

        self.word_vec = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2),
            min_df=1, max_features=20000, sublinear_tf=True,
        )
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_features=30000, sublinear_tf=True,
        )
        self.compact_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_features=30000, sublinear_tf=True,
        )
        self.word_vec.fit(norm_texts)
        self.char_vec.fit(norm_texts)
        self.compact_vec.fit(comp_texts)

    def _sparse(self, texts: Sequence[str]) -> csr_matrix:
        norm_texts = [normalize(t) for t in texts]
        comp_texts = [compact(t) for t in texts]
        w = self.word_vec.transform(norm_texts)
        c = self.char_vec.transform(norm_texts)
        c2 = self.compact_vec.transform(comp_texts)
        m = np.array([manual_features(t) for t in texts], dtype=np.float32)
        return hstack([w, c, c2, csr_matrix(m)]).tocsr()

    def _dense(self, texts: Sequence[str], fit: bool = False) -> np.ndarray:
        X = self._sparse(texts)
        if fit:
            n_comp = min(self.N_SVD, X.shape[1] - 1, X.shape[0] - 1)
            self.svd = TruncatedSVD(n_components=n_comp, random_state=42)
            return self.svd.fit_transform(X)
        return self.svd.transform(X)

    def train(self, texts, labels) -> Dict[str, Any]:
        texts = list(texts)
        labels = list(labels)
        n_pos = int(sum(labels))
        n_total = len(labels)

        if n_total < self.MIN_TOTAL or n_pos < self.MIN_POSITIVES:
            logger.warning("Мало данных GBM: total=%d, pos=%d", n_total, n_pos)
            return {"trained": False, "n_total": n_total, "n_pos": n_pos}

        self._fit_vectorizers(texts)
        X = self._dense(texts, fit=True)
        y = np.array(labels)

        self.clf = HistGradientBoostingClassifier(
            max_depth=6,
            learning_rate=0.08,
            max_iter=300,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=42,
        )
        self.clf.fit(X, y)

        self.n_pos = n_pos
        self.n_total = n_total
        logger.info("HistGBM обучен: total=%d, pos=%d", n_total, n_pos)
        return {"trained": True, "n_total": n_total, "n_pos": n_pos}

    def predict(self, text: str) -> Prediction:
        if self.clf is None or self.word_vec is None or self.svd is None:
            return Prediction(False, 0.0, 0.0, "gbm_untrained")
        try:
            X = self._dense([text])
        except Exception as e:
            logger.error("gbm transform error: %s", e)
            return Prediction(False, 0.0, 0.0, "gbm_error")

        if X.shape[1] != self.clf.n_features_in_:
            logger.error(
                "gbm feature mismatch: got %d, expected %d",
                X.shape[1], self.clf.n_features_in_,
            )
            return Prediction(False, 0.0, 0.0, "gbm_feature_mismatch")

        proba = float(self.clf.predict_proba(X)[0, 1])
        is_spam = proba >= self.threshold
        return Prediction(
            is_spam=is_spam,
            confidence=proba if is_spam else 1.0 - proba,
            proba=proba,
            reason="gbm_model",
        )

    def save(self) -> None:
        if self.clf is None:
            return
        path = self.model_dir / "model.pkl"
        with path.open("wb") as f:
            pickle.dump({
                "word_vec": self.word_vec,
                "char_vec": self.char_vec,
                "compact_vec": self.compact_vec,
                "svd": self.svd,
                "clf": self.clf,
                "threshold": self.threshold,
                "n_pos": self.n_pos,
                "n_total": self.n_total,
            }, f)
        logger.info("gbm сохранён: %s", path)

    def load(self) -> bool:
        path = self.model_dir / "model.pkl"
        if not path.exists():
            return False
        with path.open("rb") as f:
            data = pickle.load(f)
        self.word_vec = data["word_vec"]
        self.char_vec = data["char_vec"]
        self.compact_vec = data.get("compact_vec")
        self.svd = data["svd"]
        self.clf = data["clf"]
        self.threshold = data["threshold"]
        self.n_pos = data.get("n_pos", 0)
        self.n_total = data.get("n_total", 0)
        return True