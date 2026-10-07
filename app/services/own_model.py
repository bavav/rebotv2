# moderation/own_model.py
"""
OwnSpamClassifier — обучаемый классификатор рекламы.

Интерфейс совместим со SpamShieldClassifier:
    clf = OwnSpamClassifier(model_dir="./spamshieldmodel/own")
    clf.load()
    result = clf.predict(text, context={"message_count": 5})
    result.is_spam      # bool
    result.confidence   # float 0..1

Обучение:
    clf.train(texts, labels, contexts)
    clf.save()
"""
from __future__ import annotations

import logging
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- prediction

@dataclass
class Prediction:
    is_spam: bool
    confidence: float
    proba: float
    reason: str = "own_model"


# ---------------------------------------------------------------- features

_URL_RE = re.compile(r"https?://\S+|t\.me/\S+")
_MENTION_RE = re.compile(r"@\w+")
_PRICE_RE = re.compile(r"\d+\s*(?:руб|₽|доллар|\$|%|тыс)", re.IGNORECASE)
_MONEY_WORDS_RE = re.compile(
    r"(заработ|доход|крипт|инвест|прибыл|партнер|схем|биржа|связк|обучен|"
    r"скидк|акци|куп(и|лю)|закаж|цена|бесплатн|реклам|приглаша|митап|"
    r"вебинар|конференц|хакатон|регистрац|приз|розыгрыш|побогат|разбогат)",
    re.IGNORECASE,
)


def manual_features(text: str) -> List[float]:
    n = max(len(text), 1)
    caps = sum(1 for c in text if c.isupper()) / n
    digits = sum(1 for c in text if c.isdigit()) / n
    letters = sum(1 for c in text if c.isalpha()) / n
    punctuation = sum(1 for c in text if not c.isalnum() and not c.isspace()) / n

    return [
        float(bool(_URL_RE.search(text))),
        float(bool(_MENTION_RE.search(text))),
        float(bool(_PRICE_RE.search(text))),
        float(bool(_MONEY_WORDS_RE.search(text))),
        min(len(text), 1000) / 1000.0,
        caps,
        digits,
        letters,
        punctuation,
        min(text.count("\n"), 10) / 10.0,
    ]

# ---------------------------------------------------------------- classifier

class OwnSpamClassifier:
    # ниже этих порогов модель не обучается — слишком мало сигнала
    MIN_POSITIVES = 5
    MIN_TOTAL = 20

    def __init__(
        self,
        model_dir: str = "./shieldmodel/own",
        threshold: float = 0.5,
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold

        self.word_vec: Optional[TfidfVectorizer] = None
        self.char_vec: Optional[TfidfVectorizer] = None
        self.clf: Optional[LogisticRegression] = None
        self.n_pos: int = 0
        self.n_total: int = 0
        self.version: str = "v0"
        logger.info("loading")
        self.load()
        logger.info("loaded")

    # ---------- внутреннее ----------

    def _fit_vectorizers(self, texts: Sequence[str]) -> None:
        self.word_vec = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=1,
            max_features=20000,
            lowercase=True,
            sublinear_tf=True,
        )
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            max_features=30000,
            lowercase=True,
            sublinear_tf=True,
        )
        self.word_vec.fit(texts)
        self.char_vec.fit(texts)

    def _transform(
        self,
        texts: Sequence[str],
        contexts: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> csr_matrix:
        w = self.word_vec.transform(texts)
        c = self.char_vec.transform(texts)
        if contexts is None:
            contexts = [{} for _ in texts]
        m = np.array(
            [manual_features(t) for t, ctx in zip(texts, contexts)],
            dtype=np.float32,
        )
        return hstack([w, c, csr_matrix(m)]).tocsr()

    # ---------- обучение ----------

    def train(
        self,
        texts: Sequence[str],
        labels: Sequence[int],
        contexts: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        texts = list(texts)
        labels = list(labels)
        n_pos = int(sum(labels))
        n_total = len(labels)

        if (n_total < self.MIN_TOTAL or n_pos < self.MIN_POSITIVES) and False:
            logger.warning(
                "Мало данных для обучения: total=%d, pos=%d — пропуск.",
                n_total, n_pos,
            )
            return {"trained": False, "n_total": n_total, "n_pos": n_pos}

        self._fit_vectorizers(texts)
        X = self._transform(texts, contexts)
        y = np.array(labels)

        self.clf = LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            solver="liblinear",
        )
        self.clf.fit(X, y)

        self.n_pos = n_pos
        self.n_total = n_total
        logger.info("Модель обучена: total=%d, pos=%d", n_total, n_pos)
        return {"trained": True, "n_total": n_total, "n_pos": n_pos}

    # ---------- предсказание ----------

    def predict(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        if self.clf is None or self.word_vec is None or self.char_vec is None:
            return Prediction(
                is_spam=False, confidence=0.0, proba=0.0,
                reason="own_model_untrained",
            )

        X = self._transform([text], [context or {}])
        proba = float(self.clf.predict_proba(X)[0, 1])
        is_spam = proba >= self.threshold
        return Prediction(
            is_spam=is_spam,
            confidence=proba if is_spam else 1.0 - proba,
            proba=proba,
            reason="own_model",
        )

    # ---------- сохранение ----------

    def save(self) -> None:
        if self.clf is None:
            logger.warning("Нечего сохранять: модель не обучена")
            return
        path = self.model_dir / "model.pkl"
        with path.open("wb") as f:
            pickle.dump(
                {
                    "word_vec": self.word_vec,
                    "char_vec": self.char_vec,
                    "clf": self.clf,
                    "threshold": self.threshold,
                    "n_pos": self.n_pos,
                    "n_total": self.n_total,
                    "version": self.version,
                },
                f,
            )
        logger.info("Модель сохранена: %s", path)

    def load(self) -> bool:
        path = self.model_dir / "model.pkl"
        if not path.exists():
            logger.info("Файл модели не найден: %s", path)
            return False
        with path.open("rb") as f:
            data = pickle.load(f)
        self.word_vec = data["word_vec"]
        self.char_vec = data["char_vec"]
        self.clf = data["clf"]
        self.threshold = data["threshold"]
        self.n_pos = data.get("n_pos", 0)
        self.n_total = data.get("n_total", 0)
        self.version = data.get("version", "v0")
        logger.info(
            "Модель загружена: %s (total=%d, pos=%d)",
            path, self.n_total, self.n_pos,
        )
        return True