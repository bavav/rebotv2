# moderation/cascade.py
from __future__ import annotations

import logging

from .own_model import OwnSpamClassifier, Prediction
from .gbm_model import GradientBoostingSpamClassifier
from .svm_model import SVMEmbeddingSpamClassifier

logger = logging.getLogger(__name__)


class Cascade:
    def __init__(self, lo: float = 0.4, hi: float = 0.7) -> None:
        self.lo = lo
        self.hi = hi

        self.logreg = OwnSpamClassifier("./workers/ads_worker/app/shieldmodel/own")
        self.gbm = GradientBoostingSpamClassifier("./workers/ads_worker/app/shieldmodel/gbm")
        self.svm = SVMEmbeddingSpamClassifier("./workers/ads_worker/app/shieldmodel/svm")

        self._lr_ok = self.logreg.load()
        self._gbm_ok = self.gbm.load()
        self._svm_ok = self.svm.load()

        logger.info(
            "Cascade loaded: logreg=%s, gbm=%s, svm=%s",
            self._lr_ok, self._gbm_ok, self._svm_ok,
        )

    def predict(self, text: str) -> Prediction:
        # Stage 1: LogReg
        if self._lr_ok:
            p1 = self.logreg.predict(text).proba
            if p1 < self.lo:
                return Prediction(False, 1 - p1, p1, "cascade_logreg_safe")
            if p1 > self.hi:
                return Prediction(True, p1, p1, "cascade_logreg_spam")
        else:
            p1 = 0.5

        # Stage 2: GBM
        if self._gbm_ok:
            p2 = self.gbm.predict(text).proba

            # Ранний выход по согласию двух моделей
            if abs(p1 - p2) < 0.1:
                avg = (p1 + p2) / 2.0
                is_spam = avg >= 0.5
                return Prediction(
                    is_spam=is_spam,
                    confidence=max(p1, p2) if is_spam else 1 - min(p1, p2),
                    proba=avg,
                    reason="cascade_lr_gbm_agree",
                )

            if p2 < self.lo:
                return Prediction(False, 1 - p2, p2, "cascade_gbm_safe")
            if p2 > self.hi:
                return Prediction(True, p2, p2, "cascade_gbm_spam")
        else:
            p2 = 0.5

        # Stage 3: SVM — финальный вердикт
        if self._svm_ok:
            p3 = self.svm.predict(text).proba
            is_spam = p3 >= 0.5
            return Prediction(
                is_spam=is_spam,
                confidence=p3 if is_spam else 1 - p3,
                proba=p3,
                reason="cascade_svm",
            )

        # фолбэк: усреднение того, что есть
        avg = (p1 + p2) / 2.0
        is_spam = avg >= 0.5
        return Prediction(
            is_spam=is_spam,
            confidence=avg if is_spam else 1 - avg,
            proba=avg,
            reason="cascade_fallback",
        )


cascade = Cascade()