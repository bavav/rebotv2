# ml_model.py
import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from concurrent.futures import ThreadPoolExecutor

import torch
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Конфигурация модели"""
    model_name: str = 'ruSpamModels/ruSpam_big'
    threshold: float = 0.5
    spam_template: str = "спам реклама предложение услуга скидка акция мошенничество"
    safe_template: str = "привет как дела хороший день нормальное общение"
    use_cache: bool = True
    cache_size: int = 1024
    min_text_length: int = 3


@dataclass
class PredictionResult:
    """Результат предсказания"""
    is_spam: bool
    confidence: float
    spam_score: float
    safe_score: float
    model_name: str
    threshold: float


class EmbeddingCache:
    """Кэш для эмбеддингов"""
    
    def __init__(self, maxsize: int = 1024):
        self._cache: Dict[str, torch.Tensor] = {}
        self._maxsize = maxsize
    
    def get(self, text: str) -> Optional[torch.Tensor]:
        key = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return self._cache.get(key)
    
    def set(self, text: str, embedding: torch.Tensor):
        if len(self._cache) >= self._maxsize:
            # LRU: удаляем первый элемент
            self._cache.pop(next(iter(self._cache)))
        key = hashlib.sha256(text.encode('utf-8')).hexdigest()
        self._cache[key] = embedding
    
    def clear(self):
        self._cache.clear()


class SpamClassifier:
    """
    Классификатор спама с использованием sentence transformers.
    Поддерживает кэширование, асинхронную загрузку и множество моделей.
    """
    
    AVAILABLE_MODELS = [
        'ruSpamModels/ruSpam_big',
        'ruSpamModels/ruSpam_small',
        'cointegrated/rubert-tiny-toxicity',
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    ]
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self._model: Optional[SentenceTransformer] = None
        self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._cache = EmbeddingCache(self.config.cache_size) if self.config.use_cache else None
        self.tupe = "noshield"
        # Эмбеддинги шаблонов
        self._spam_embedding: Optional[torch.Tensor] = None
        self._safe_embedding: Optional[torch.Tensor] = None
        
        # Загружаем модель
        self._load_model(self.config.model_name)
        self._update_template_embeddings()
        
        logger.info(f"✅ Классификатор инициализирован на {self._device}")
        logger.info(f"   Модель: {self.config.model_name}")
        logger.info(f"   Порог: {self.config.threshold}")
        logger.info(f"   Кэш: {'включен' if self.config.use_cache else 'выключен'}")
    
    def _load_model(self, model_name: str) -> bool:
        """Загружает модель с fallback на дефолтную"""
        try:
            if self._model is not None:
                del self._model
                self._clear_gpu_memory()
            
            logger.info(f"🔄 Загрузка модели: {model_name}")
            self._model = SentenceTransformer(model_name, device=self._device)
            self.config.model_name = model_name
            self._update_template_embeddings()
            logger.info(f"✅ Модель загружена: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {model_name}: {e}")
            
            # Fallback на дефолтную модель
            if model_name != self.AVAILABLE_MODELS[0]:
                logger.info(f"🔄 Пробуем загрузить модель по умолчанию...")
                return self._load_model(self.AVAILABLE_MODELS[0])
            return False
    
    def _clear_gpu_memory(self):
        """Очищает память GPU"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def _update_template_embeddings(self):
        """Обновляет эмбеддинги шаблонов"""
        if self._model is None:
            return
        
        self._spam_embedding = self._encode(self.config.spam_template)
        self._safe_embedding = self._encode(self.config.safe_template)
    
    def _encode(self, text: str) -> Optional[torch.Tensor]:
        """Кодирует текст в эмбеддинг с использованием кэша"""
        if not text or self._model is None:
            return None
        
        # Проверяем кэш
        if self._cache:
            cached = self._cache.get(text)
            if cached is not None:
                return cached
        
        # Кодируем
        try:
            embedding = self._model.encode(
                text,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            # Сохраняем в кэш
            if self._cache:
                self._cache.set(text, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Ошибка кодирования: {e}")
            return None
    
    def set_threshold(self, threshold: float):
        """Устанавливает порог уверенности"""
        if 0 <= threshold <= 1:
            self.config.threshold = threshold
            logger.info(f"📊 Порог изменен: {threshold}")
    
    def set_templates(self, spam_text: str, safe_text: str):
        """Устанавливает шаблоны для сравнения"""
        self.config.spam_template = spam_text
        self.config.safe_template = safe_text
        self._update_template_embeddings()
        if self._cache:
            self._cache.clear()
        logger.info("🔄 Шаблоны обновлены")
    
    def switch_model(self, model_name: str) -> bool:
        """Переключает модель"""
        if model_name not in self.AVAILABLE_MODELS:
            logger.warning(f"⚠️ Модель {model_name} не в списке доступных")
            return False
        
        if self._load_model(model_name):
            if self._cache:
                self._cache.clear()
            return True
        return False
    
    def predict(self, text: str) -> PredictionResult:
        """
        Синхронное предсказание
        
        Args:
            text: Текст для классификации
            
        Returns:
            PredictionResult с результатами
        """
        text = text.strip()
        
        # Проверка валидности
        if not text or len(text) < self.config.min_text_length:
            return PredictionResult(
                is_spam=False,
                confidence=0.0,
                spam_score=0.0,
                safe_score=0.0,
                model_name=self.config.model_name,
                threshold=self.config.threshold
            )
        
        if self._model is None or self._spam_embedding is None:
            logger.warning("⚠️ Модель не загружена")
            return self._empty_result()
        
        try:
            # Получаем эмбеддинг текста
            text_embedding = self._encode(text)
            if text_embedding is None:
                return self._empty_result()
            
            # Вычисляем схожесть
            spam_sim = util.cos_sim(text_embedding, self._spam_embedding).item()
            safe_sim = util.cos_sim(text_embedding, self._safe_embedding).item()
            
            # Вычисляем уверенность
            confidence = self._calculate_confidence(spam_sim, safe_sim)
            is_spam = confidence > self.config.threshold
            
            return PredictionResult(
                is_spam=is_spam,
                confidence=confidence,
                spam_score=spam_sim,
                safe_score=safe_sim,
                model_name=self.config.model_name,
                threshold=self.config.threshold
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка предсказания: {e}")
            return self._empty_result()
    
    async def predict_async(self, text: str) -> PredictionResult:
        """Асинхронное предсказание"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.predict, text)
    
    def predict_batch(self, texts: list) -> list:
        """Пакетное предсказание для нескольких текстов"""
        return [self.predict(text) for text in texts]
    
    async def predict_batch_async(self, texts: list) -> list:
        """Асинхронное пакетное предсказание"""
        tasks = [self.predict_async(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def _calculate_confidence(self, spam_sim: float, safe_sim: float) -> float:
        """Рассчитывает уверенность в классификации"""
        if spam_sim > 0.1 or safe_sim > 0.1:
            conf = spam_sim / (spam_sim + safe_sim + 1e-6)
        else:
            conf = 0.0
        return max(0.0, min(1.0, conf))
    
    def _empty_result(self) -> PredictionResult:
        """Возвращает пустой результат"""
        return PredictionResult(
            is_spam=False,
            confidence=0.0,
            spam_score=0.0,
            safe_score=0.0,
            model_name=self.config.model_name,
            threshold=self.config.threshold
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику классификатора"""
        return {
            'model': self.config.model_name,
            'device': self._device,
            'threshold': self.config.threshold,
            'cache_size': len(self._cache._cache) if self._cache else 0,
            'available_models': self.AVAILABLE_MODELS
        }
    
    def clear_cache(self):
        """Очищает кэш эмбеддингов"""
        if self._cache:
            self._cache.clear()
            logger.info("🗑️ Кэш очищен")
    
    def __del__(self):
        """Деструктор для очистки ресурсов"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        self._clear_gpu_memory()
    
    @classmethod
    def get_available_models(cls) -> list:
        """Получить список доступных моделей"""
        return cls.AVAILABLE_MODELS.copy()


# Синглтон через контекстный менеджер (более безопасный подход)
class SpamClassifierSingleton:
    """Контекстный менеджер для работы с синглтоном"""
    _instance: Optional[SpamClassifier] = None
    
    @classmethod
    def get_instance(cls) -> SpamClassifier:
        if cls._instance is None:
            cls._instance = SpamClassifier()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Сброс синглтона (для тестирования)"""
        if cls._instance is not None:
            del cls._instance
            cls._instance = None


# Удобная фабрика для создания классификатора
def create_classifier(
    model_name: str = 'ruSpamModels/ruSpam_big',
    threshold: float = 0.5,
    use_cache: bool = True
) -> SpamClassifier:
    """Фабрика для создания классификатора"""
    config = ModelConfig(
        model_name=model_name,
        threshold=threshold,
        use_cache=use_cache
    )
    return SpamClassifier(config)