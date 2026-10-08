# moderation/own_model.py
"""
OwnSpamClassifier — LogReg поверх TF-IDF (word + char + compact-char) + meta.

Интерфейс:
    clf = OwnSpamClassifier(model_dir="./shieldmodel/own")
    clf.load()
    result = clf.predict(text, context={...})
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

from .normalize import (
    normalize, compact,
    has_spaced_letters, has_zw_inside_word,
    has_unicode_obfuscation, obfuscation_ratio,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- prediction

@dataclass
class Prediction:
    is_spam: bool
    confidence: float
    proba: float
    reason: str = "own_model"


# ---------------------------------------------------------------- regex

_URL_RE = re.compile(r"https?://\S+|t\.me/\S+")
_MENTION_RE = re.compile(r"@\w+")
_PRICE_RE = re.compile(r"\d+\s*(?:руб|₽|доллар|\$|%|тыс)", re.IGNORECASE)

_MONEY_WORDS_RE = re.compile(
    r"(заработ|доход|крипт|инвест|прибыл|партнер|схем|биржа|связк|обучен|"
    r"скидк|акци|куп(и|лю)|закаж|цена|бесплатн|реклам|приглаша|митап|"
    r"вебинар|конференц|хакатон|регистрац|приз|розыгрыш|побогат|разбогат|"
    r"кейс|кейсов|казино|рулетк|ставк|фриспин|депозит|вейджер|кэшбэк|"
    r"кешбэк|джекпот|краш|гайд|схема|стратегия)",
    re.IGNORECASE,
)

_CASINO_KW = (
    "казино", "казик", "кейс", "keys", "рулетк", "ставк", "ставок",
    "фриспин", "фриспин", "депозит", "вейджер", "бонус", "кэшбэк", "кешбэк",
    "краш", "джекпот", "слот", "лудоман", "гэмблинг", "рулет", "ставк",
)
_PROMO_KW = (
    "промокод", "промокод", "рефк", "реферал", "фриспин", "по ссылке",
    "по моей", "в лс", "влс", "пиши", "залетай", "рега",
)

_CTA_RE = re.compile(
    r"(пиши|залетай|регайся|регистрируйся|подписывайся|жми|лови|успей|"
    r"забирай|переходи|оформляй|бонус новичк)",
    re.IGNORECASE,
)
_REF_RE = re.compile(
    r"(рефк|реферал|по моей ссылке|по ссылке|промокод|промо-?код|рег по)",
    re.IGNORECASE,
)
_DISCLAIMER_RE = re.compile(
    r"(не реклама|это не реклама|просто советую|просто делюсь)",
    re.IGNORECASE,
)
_MAT_OBF_RE = re.compile(
    r"(бл[\*@#]?[тья]|х[\*@#]?й|п[\*@#]?зд|оху|ахуе|муд[ао]к)",
    re.IGNORECASE,
)
_MAT_RAW_RE = re.compile(
    r"(блять|хуй|пиздец|охуел|мудак|долбоёб)",
    re.IGNORECASE,
)


def _fuzzy_has(text: str, keywords: tuple[str, ...]) -> bool:
    c = compact(text)
    return any(k in c for k in keywords)


# ---------------------------------------------------------------- features

def manual_features(text: str) -> List[float]:
    n = max(len(text), 1)
    caps = sum(1 for c in text if c.isupper()) / n
    digits = sum(1 for c in text if c.isdigit()) / n
    letters = sum(1 for c in text if c.isalpha()) / n
    punct = sum(1 for c in text if not c.isalnum() and not c.isspace()) / n

    return [
        # базовая разметка
        float(bool(_URL_RE.search(text))),
        float(bool(_MENTION_RE.search(text))),
        float(bool(_PRICE_RE.search(text))),
        float(bool(_MONEY_WORDS_RE.search(text))),

        # тематика целевого чата
        float(_fuzzy_has(text, _CASINO_KW)),
        float(_fuzzy_has(text, _PROMO_KW)),

        # рекламные маркеры
        float(bool(_CTA_RE.search(text))),
        float(bool(_REF_RE.search(text))),
        float(bool(_DISCLAIMER_RE.search(text))),

        # мат: обфусцированный — живой юзер; сырой — бот
        float(bool(_MAT_OBF_RE.search(text))),
        float(bool(_MAT_RAW_RE.search(text))),

        # обфускация как признак бота
        float(has_spaced_letters(text)),
        float(has_zw_inside_word(text)),
        float(has_unicode_obfuscation(text)),
        obfuscation_ratio(text),

        # форма
        min(len(text), 1000) / 1000.0,
        caps, digits, letters, punct,
        min(text.count("\n"), 10) / 10.0,
    ]


# ---------------------------------------------------------------- classifier

class OwnSpamClassifier:
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
        self.compact_vec: Optional[TfidfVectorizer] = None
        self.clf: Optional[LogisticRegression] = None
        self.n_pos: int = 0
        self.n_total: int = 0
        self.version: str = "v1"

    # ---------- внутреннее ----------

    def _fit_vectorizers(self, texts: Sequence[str]) -> None:
        norm_texts = [normalize(t) for t in texts]
        comp_texts = [compact(t) for t in texts]

        self.word_vec = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2),
            min_df=1, max_features=20000,
            sublinear_tf=True,
        )
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_features=30000,
            sublinear_tf=True,
        )
        self.compact_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_features=30000,
            sublinear_tf=True,
        )

        self.word_vec.fit(norm_texts)
        self.char_vec.fit(norm_texts)
        self.compact_vec.fit(comp_texts)

    def _transform(
        self,
        texts: Sequence[str],
        contexts: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> csr_matrix:
        norm_texts = [normalize(t) for t in texts]
        comp_texts = [compact(t) for t in texts]

        w = self.word_vec.transform(norm_texts)
        c = self.char_vec.transform(norm_texts)
        c2 = self.compact_vec.transform(comp_texts)

        if contexts is None:
            contexts = [{} for _ in texts]
        m = np.array(
            [manual_features(t) for t in texts],
            dtype=np.float32,
        )
        return hstack([w, c, c2, csr_matrix(m)]).tocsr()

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

        if n_total < self.MIN_TOTAL or n_pos < self.MIN_POSITIVES:
            logger.warning(
                "Мало данных: total=%d, pos=%d — пропуск.", n_total, n_pos,
            )
            return {"trained": False, "n_total": n_total, "n_pos": n_pos}

        self._fit_vectorizers(texts)
        X = self._transform(texts, contexts)
        y = np.array(labels)

        self.clf = LogisticRegression(
            C=1.0, max_iter=2000,
            class_weight="balanced",
            solver="liblinear",
        )
        self.clf.fit(X, y)

        self.n_pos = n_pos
        self.n_total = n_total
        logger.info("LogReg обучен: total=%d, pos=%d", n_total, n_pos)
        return {"trained": True, "n_total": n_total, "n_pos": n_pos}

    # ---------- предсказание ----------

    def predict(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        if self.clf is None or self.word_vec is None:
            return Prediction(False, 0.0, 0.0, "own_model_untrained")
        try:
            X = self._transform([text], [context or {}])
        except Exception as e:
            logger.error("own_model transform error: %s", e)
            return Prediction(False, 0.0, 0.0, "own_model_error")

        if X.shape[1] != self.clf.n_features_in_:
            logger.error(
                "own_model feature mismatch: got %d, expected %d",
                X.shape[1], self.clf.n_features_in_,
            )
            return Prediction(False, 0.0, 0.0, "own_model_feature_mismatch")

        proba = float(self.clf.predict_proba(X)[0, 1])
        is_spam = proba >= self.threshold
        return Prediction(
            is_spam=is_spam,
            confidence=proba if is_spam else 1.0 - proba,
            proba=proba,
            reason="own_model",
        )

    # ---------- персистентность ----------

    def save(self) -> None:
        if self.clf is None:
            logger.warning("Нечего сохранять: модель не обучена")
            return
        path = self.model_dir / "model.pkl"
        with path.open("wb") as f:
            pickle.dump({
                "word_vec": self.word_vec,
                "char_vec": self.char_vec,
                "compact_vec": self.compact_vec,
                "clf": self.clf,
                "threshold": self.threshold,
                "n_pos": self.n_pos,
                "n_total": self.n_total,
                "version": self.version,
            }, f)
        logger.info("own_model сохранён: %s", path)

    def load(self) -> bool:
        path = self.model_dir / "model.pkl"
        if not path.exists():
            logger.info("own_model: файла нет %s", path)
            return False
        with path.open("rb") as f:
            data = pickle.load(f)
        self.word_vec = data["word_vec"]
        self.char_vec = data["char_vec"]
        # старые сохранения без compact_vec — совместимость
        self.compact_vec = data.get("compact_vec")
        self.clf = data["clf"]
        self.threshold = data["threshold"]
        self.n_pos = data.get("n_pos", 0)
        self.n_total = data.get("n_total", 0)
        self.version = data.get("version", "v0")
        logger.info(
            "own_model загружен: %s (total=%d, pos=%d, ver=%s)",
            path, self.n_total, self.n_pos, self.version,
        )
        return True