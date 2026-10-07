# moderation/svm_embedding_model.py
"""
SVMEmbeddingSpamClassifier — SVM поверх эмбеддингов.

Использует мультиязычную/русскую модель эмбеддингов,
усредняет токены в один вектор, обучает SVM с RBF-ядром.

Интерфейс совместим с OwnSpamClassifier.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.svm import SVC

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
        model_dir: str = "./shieldmodel/svm_emb",
        threshold: float = 0.5,
        embedding_model: str = "cointegrated/rubert-tiny2",
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.embedding_model_name = embedding_model

        self.embedder = None
        self.clf: Optional[CalibratedClassifierCV] = None
        self.n_pos: int = 0
        self.n_total: int = 0

    def _load_embedder(self):
        if self.embedder is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer(self.embedding_model_name)
            logger.info("Эмбеддер загружен: %s", self.embedding_model_name)
        except ImportError:
            logger.error(
                "sentence-transformers не установлен. "
                
            )
            raise

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        self._load_embedder()
        # encode с нормализацией — косинус будет через скалярное произведение
        embs = self.embedder.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embs, dtype=np.float32)

    def train(
        self,
        texts: Sequence[str],
        labels: Sequence[int],
    ) -> Dict[str, object]:
        texts = list(texts)
        labels = list(labels)
        n_pos = int(sum(labels))
        n_total = len(labels)

        if n_total < self.MIN_TOTAL or n_pos < self.MIN_POSITIVES:
            logger.warning(
                "Мало данных для SVM: total=%d, pos=%d — пропуск.",
                n_total, n_pos,
            )
            return {"trained": False, "n_total": n_total, "n_pos": n_pos}

        X = self._embed(texts)
        y = np.array(labels)

        # SVC с RBF — стандарт для текстов на эмбеддингах.
        # probability=True нужен для predict_proba.
        base_svc = SVC(
            kernel="rbf",
            C=1.0,
            gamma="scale",
            class_weight="balanced",
            random_state=42,
        )
        self.clf = CalibratedClassifierCV(
            base_svc,
            method="sigmoid",   # аналог Platt scaling
            cv=3,               # 3-fold хватает, не 5 — быстрее
        )
        self.clf.fit(X, y)

        self.n_pos = n_pos
        self.n_total = n_total
        logger.info("SVM обучен: total=%d, pos=%d", n_total, n_pos)
        return {"trained": True, "n_total": n_total, "n_pos": n_pos}

    def predict(self, text: str) -> Prediction:
        if self.clf is None:
            return Prediction(False, 0.0, 0.0, "svm_untrained")

        X = self._embed([text])
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
                "threshold": self.threshold,
                "embedding_model_name": self.embedding_model_name,
                "n_pos": self.n_pos,
                "n_total": self.n_total,
            }, f)
        logger.info("SVM сохранён: %s", path)

    def load(self) -> bool:
        path = self.model_dir / "model.pkl"
        if not path.exists():
            return False
        with path.open("rb") as f:
            data = pickle.load(f)
        self.clf = data["clf"]
        self.threshold = data["threshold"]
        self.embedding_model_name = data.get("embedding_model_name", self.embedding_model_name)
        self.n_pos = data.get("n_pos", 0)
        self.n_total = data.get("n_total", 0)
        return True