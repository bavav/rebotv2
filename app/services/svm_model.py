# moderation/svm_model.py
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .normalize import normalize
from .own_model import manual_features

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    is_spam: bool
    confidence: float
    proba: float
    reason: str = "svm_embedding"


class SVMEmbeddingSpamClassifier:
    MIN_POSITIVES = 5
    MIN_TOTAL = 20

    def __init__(
        self,
        model_dir: str = "./shieldmodel/svm",
        threshold: float = 0.5,
        embedding_model: str = "cointegrated/rubert-tiny2",
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.embedding_model_name = embedding_model

        self.embedder = None
        self.scaler: Optional[StandardScaler] = None
        self.clf: Optional[CalibratedClassifierCV] = None
        self.n_pos: int = 0
        self.n_total: int = 0

    def _load_embedder(self):
        if self.embedder is not None:
            return
        from sentence_transformers import SentenceTransformer
        self.embedder = SentenceTransformer(self.embedding_model_name)
        logger.info("Эмбеддер загружен: %s", self.embedding_model_name)

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        self._load_embedder()
        norm_texts = [normalize(t) for t in texts]
        embs = self.embedder.encode(
            norm_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embs, dtype=np.float32)

    def _features(self, texts: Sequence[str], fit: bool = False) -> np.ndarray:
        embs = self._embed(texts)
        meta = np.array([manual_features(t) for t in texts], dtype=np.float32)
        if fit:
            # scale только meta, эмбеддинги уже нормализованы
            self.scaler = StandardScaler()
            meta = self.scaler.fit_transform(meta)
        else:
            meta = self.scaler.transform(meta)
        return np.hstack([embs, meta]).astype(np.float32)

    def train(self, texts, labels) -> Dict[str, Any]:
        texts = list(texts)
        labels = list(labels)
        n_pos = int(sum(labels))
        n_total = len(labels)

        if n_total < self.MIN_TOTAL or n_pos < self.MIN_POSITIVES:
            logger.warning("Мало данных SVM: total=%d, pos=%d", n_total, n_pos)
            return {"trained": False, "n_total": n_total, "n_pos": n_pos}

        X = self._features(texts, fit=True)
        y = np.array(labels)

        base = SVC(
            kernel="rbf",
            C=1.0,
            gamma="scale",
            class_weight="balanced",
            random_state=42,
        )
        n_splits = 3 if n_pos < 15 else 5
        self.clf = CalibratedClassifierCV(base, method="sigmoid", cv=n_splits)
        self.clf.fit(X, y)

        self.n_pos = n_pos
        self.n_total = n_total
        logger.info("SVM обучен: total=%d, pos=%d, dim=%d", n_total, n_pos, X.shape[1])
        return {"trained": True, "n_total": n_total, "n_pos": n_pos}

    def predict(self, text: str) -> Prediction:
        if self.clf is None or self.scaler is None:
            return Prediction(False, 0.0, 0.0, "svm_untrained")
        try:
            X = self._features([text])
        except Exception as e:
            logger.error("svm error: %s", e)
            return Prediction(False, 0.0, 0.0, "svm_error")

        if X.shape[1] != self.clf.n_features_in_:
            logger.error(
                "svm dim mismatch: got %d, expected %d",
                X.shape[1], self.clf.n_features_in_,
            )
            return Prediction(False, 0.0, 0.0, "svm_dim_mismatch")

        proba = float(self.clf.predict_proba(X)[0, 1])
        is_spam = proba >= self.threshold
        return Prediction(
            is_spam=is_spam,
            confidence=proba if is_spam else 1.0 - proba,
            proba=proba,
            reason="svm_embedding",
        )

    def save(self) -> None:
        if self.clf is None:
            return
        path = self.model_dir / "model.pkl"
        with path.open("wb") as f:
            pickle.dump({
                "clf": self.clf,
                "scaler": self.scaler,
                "threshold": self.threshold,
                "embedding_model_name": self.embedding_model_name,
                "n_pos": self.n_pos,
                "n_total": self.n_total,
            }, f)
        logger.info("svm сохранён: %s", path)

    def load(self) -> bool:
        path = self.model_dir / "model.pkl"
        if not path.exists():
            return False
        with path.open("rb") as f:
            data = pickle.load(f)
        self.clf = data["clf"]
        self.scaler = data.get("scaler")   # None для старых моделей
        self.threshold = data["threshold"]
        self.embedding_model_name = data.get(
            "embedding_model_name", self.embedding_model_name,
        )
        self.n_pos = data.get("n_pos", 0)
        self.n_total = data.get("n_total", 0)
        return True