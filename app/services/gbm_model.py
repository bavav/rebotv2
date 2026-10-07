# moderation/gbm_model.py
"""
GradientBoostingSpamClassifier — градиентный бустинг поверх TF-IDF.

Использует те же признаки, что и LogReg (TF-IDF word + char),
но нелинейные взаимодействия через деревья решений.

Интерфейс совместим с OwnSpamClassifier:
    clf = GradientBoostingSpamClassifier(model_dir="./spamshieldmodel/gbm")
    clf.load()
    result = clf.predict(text)
    result.is_spam      # bool
    result.confidence   # float 0..1
    result.proba        # float 0..1 (вероятность спама)
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

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
        self.clf: Optional[GradientBoostingClassifier] = None
        self.n_pos: int = 0
        self.n_total: int = 0

    def _fit_vectorizers(self, texts: Sequence[str]) -> None:
        self.word_vec = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2),
            min_df=1, max_features=20000,
            lowercase=True, sublinear_tf=True,
        )
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_features=30000,
            lowercase=True, sublinear_tf=True,
        )
        self.word_vec.fit(texts)
        self.char_vec.fit(texts)

    def _transform(self, texts: Sequence[str]) -> csr_matrix:
        w = self.word_vec.transform(texts)
        c = self.char_vec.transform(texts)
        return hstack([w, c]).tocsr()

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
                "Мало данных для обучения GBM: total=%d, pos=%d — пропуск.",
                n_total, n_pos,
            )
            return {"trained": False, "n_total": n_total, "n_pos": n_pos}

        self._fit_vectorizers(texts)
        X = self._transform(texts)
        y = np.array(labels)

        self.clf = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
        )
        self.clf.fit(X, y)

        self.n_pos = n_pos
        self.n_total = n_total
        logger.info("GBM обучен: total=%d, pos=%d", n_total, n_pos)
        return {"trained": True, "n_total": n_total, "n_pos": n_pos}

    def predict(self, text: str) -> Prediction:
        if self.clf is None or self.word_vec is None or self.char_vec is None:
            return Prediction(False, 0.0, 0.0, "gbm_untrained")

        X = self._transform([text])
        expected = self.clf.n_features_in_
        if X.shape[1] != expected:
            logger.error("GBM feature mismatch: got %d, expected %d", X.shape[1], expected)
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
                "clf": self.clf,
                "threshold": self.threshold,
                "n_pos": self.n_pos,
                "n_total": self.n_total,
            }, f)
        logger.info("GBM сохранён: %s", path)

    def load(self) -> bool:
        path = self.model_dir / "model.pkl"
        if not path.exists():
            return False
        with path.open("rb") as f:
            data = pickle.load(f)
        self.word_vec = data["word_vec"]
        self.char_vec = data["char_vec"]
        self.clf = data["clf"]
        self.threshold = data["threshold"]
        self.n_pos = data.get("n_pos", 0)
        self.n_total = data.get("n_total", 0)
        return True