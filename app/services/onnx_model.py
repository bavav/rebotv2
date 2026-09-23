# app/services/onnx_model.py
import logging
import numpy as np
import onnxruntime as ort
import hashlib
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PredictionResult:
    def __init__(self, is_spam, confidence, spam_score, safe_score, model_name, threshold):
        self.is_spam = is_spam
        self.confidence = confidence
        self.spam_score = spam_score
        self.safe_score = safe_score
        self.model_name = model_name
        self.threshold = threshold


class SpamShieldClassifier:
    """
    Классификатор на основе SpamShield (ONNX).
    Вход: сырой текст → модель сама преобразует его через встроенный векторизатор.
    """
    def __init__(
        self,
        model_path: str = "./shieldmodel/",
        threshold: float = 0.5,
        use_cache: bool = True,
        cache_size: int = 2048,
    ):
        self.model_path = model_path
        self.threshold = threshold
        self._cache = {} if use_cache else None
        self.cache_size = cache_size
        self.tupe = "shield"
        # Загружаем бинарную модель (спам/не спам)
        self.binary_session = ort.InferenceSession(
            f'{model_path}/binary_model.onnx',
            providers=['CPUExecutionProvider']  # или ['CUDAExecutionProvider']
        )
        logger.info(f"✅ SpamShield (ONNX) загружен, порог={threshold}")

    def _get_cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _apply_threshold(self, result: PredictionResult) -> Optional[PredictionResult]:
        """
        Единая точка применения порога.
        Возвращает результат, если confidence > threshold, иначе None.
        """
        
        return result if result.confidence > self.threshold else None

    def predict(self, text: str) -> Optional[PredictionResult]:
        """Синхронное предсказание"""
        text = text.strip()
        
        if not text or len(text) < 3:
            return None

        # Кэш: хранит СЫРЫЕ скоры (PredictionResult), порог применяется всегда заново
        key = None
        if self._cache is not None:
            key = self._get_cache_key(text)
            cached = self._cache.get(key)
            if cached is not None:
                # ВАЖНО: применяем текущий порог к закэшированному результату
                return cached

        try:
            # Подготовка входных данных: модель ожидает массив строк (batch, 1)
            # В Quickstart: np.array([[text]], dtype=object)
            input_array = np.array([[text]], dtype=object)

            # Запуск инференса
            binary_output = self.binary_session.run(
                None,  # все выходы
                {'input': input_array}   # имя входа может быть 'input' или другое — проверить по модели
            )

            # Извлечение результата
            # binary_output[0] — метка класса (0/1)
            is_spam = bool(binary_output[0][0] == 1)
            # binary_output[1] — словарь вероятностей {0: prob0, 1: prob1}
            confidence = float(binary_output[1][0].get(1, 0.0))

            # Для совместимости с вашим кодом
            result = PredictionResult(
                is_spam=is_spam,
                confidence=confidence,
                spam_score=confidence,
                safe_score=1 - confidence,
                model_name="SpamShield",
                threshold=self.threshold
            )

            # Сохраняем в кэш СЫРОЙ результат (без применения порога)
            if self._cache is not None and key is not None:
                if len(self._cache) >= self.cache_size:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[key] = result

            # Порог применяется здесь и только здесь (для свежих результатов)
            
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка инференса: {e}")
            return None

    def set_threshold(self, threshold: float):
        if 0 <= threshold <= 1:
            self.threshold = threshold
            # Сбрасываем кэш, чтобы кэшированные PredictionResult.threshold не сбивали с толку
            self.clear_cache()
            logger.info(f"📊 Порог изменён: {threshold}, кэш сброшен")

    def clear_cache(self):
        if self._cache is not None:
            self._cache.clear()
            logger.info("🗑️ Кэш очищен")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "model": "SpamShield",
            "type": "ONNX",
            "threshold": self.threshold,
            "cache_size": len(self._cache) if self._cache else 0,
        }