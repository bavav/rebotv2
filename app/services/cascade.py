from ...app.services.own_model import OwnSpamClassifier, Prediction
from ...app.services.gbm_model import GradientBoostingSpamClassifier
from ...app.services.svm_model import SVMEmbeddingSpamClassifier
from .normalize import normalize
class Cascade:
    def __init__(self,lo=0.4, hi=0.7) -> None:
        self.logreg = OwnSpamClassifier("./workers/ads_worker/app/shieldmodel/own")
        self.gbm = GradientBoostingSpamClassifier("./workers/ads_worker/app/shieldmodel/gbm")
        self.svm = SVMEmbeddingSpamClassifier("./workers/ads_worker/app/shieldmodel/svm")
        self.lo = lo
        self.hi = hi
        self.logreg.load()
        self.gbm.load()
        self.svm.load()
    def predict(self,text) -> Prediction:
        p = self.logreg.predict(text).proba
        if p < self.lo:
            return Prediction(False, 1-p, p, "cascade_logreg_safe")
        if p > self.hi:
            return Prediction(True, p, p, "cascade_logreg_spam")

        # Stage 2: GBM
        p = self.gbm.predict(text).proba
        if p < self.lo:
            return Prediction(False, 1-p, p, "cascade_gbm_safe")
        if p > self.hi:
            return Prediction(True, p, p, "cascade_gbm_spam")

        # Stage 3: SVM — финальный вердикт
        p = self.svm.predict(text).proba
        is_spam = p >= 0.5
        return Prediction(is_spam, p if is_spam else 1-p, p, "cascade_svm")
    
cascade = Cascade()
print(cascade.predict(normalize("н а ш е к а з и н о т о п п и ш и в л с")).reason)