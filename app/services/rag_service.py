from typing import Tuple, Optional, Dict, List
import logging
from .vector_store import VectorStore
from .ml_model import SpamClassifier
from app.config import config
logger = logging.getLogger(__name__)
import re
from functools import lru_cache
from app.services.onnx_model import SpamShieldClassifier
class RAGService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.vector_store = VectorStore()
        if config.use_onnx:
            self.ml_classifier = SpamShieldClassifier(
                model_path=config.SPAMSHIELD_MODEL_PATH,
                threshold=config.ML_THRESHOLD,
            )
            logger.info("✅ RAG Service использует SpamShield (ONNX)")
            print("✅ RAG Service использует SpamShield (ONNX)")
        else:
            self.ml_classifier = SpamClassifier()
            logger.info("✅ RAG Service использует обычный классификатор")
            print("✅ RAG Service использует обычный классификатор")
        self.use_ml = True
    def _quick_heuristics(self, text: str) -> Tuple[bool, float, str]:
    # ссылки (http, telegram, t.me, etc.)
        if re.search(r'https?://\S+|@\w+|t\.me/\S+', text):
            return True, 0.95, "heuristic_url"
        # явные коммерческие фразы
        if re.search(r'(скидка|акция|купить|заказать|цена|рублей|бесплатно|реклама)', text, re.I):
            
            if re.search(r'\d+\s*[%₽руб]', text):
                return True, 0.90, "heuristic_price"
            return True, 0.85, "heuristic"
        return None
    @lru_cache(maxsize=2048)
    def check_advertisement(
        self,
        text: str,
        message_count: Optional[int] = None
    ) -> Tuple[bool, float, str, Optional[str], Optional[str]]:
        """Проверка рекламы с учётом количества сообщений пользователя."""
        # 1. Быстрые эвристики (всегда)
        qh = self._quick_heuristics(text)
        if qh:
            return (*qh, None, None)

        # 2. Стоп-слова
        if any(word in text for word in config.BAD_WORDS):
            return (True, 1.0, "badword", None, None)

        # 3. Если пользователь старый (>= 100 сообщений) — пропускаем RAG и ML
        #    (можно настроить порог в config)
        TRUSTED_THRESHOLD = getattr(config, 'TRUSTED_MESSAGE_COUNT', 25)
        if message_count is not None and message_count >= TRUSTED_THRESHOLD:
            return (False, 0.0, "trusted_user", None, None)

        # 4. RAG-проверка (только для новых)
        rag_result = self.vector_store.classify_text_advanced(text)
        if rag_result['is_ad']:
            return (
                True,
                rag_result['score'],
                f"rag_{rag_result['method']}",
                rag_result.get('closest_white'),
                rag_result.get('closest_black')
            )

        # 5. ML-проверка (только для новых)
        if self.use_ml:
            result = self.ml_classifier.predict(text)
            if result.is_spam:
                logger.info(f"🤖 ML обнаружил рекламу: {text[:50]}... (Уверенность: {result.confidence:.2f})")
                return (
                    True,
                    result.confidence,
                    "ml_classifier",
                    rag_result.get('closest_white'),
                    rag_result.get('closest_black')
                )

        return (
            False,
            rag_result['score'],
            f"rag_{rag_result['method']}",
            rag_result.get('closest_white'),
            rag_result.get('closest_black')
        )
    
    def add_white_example(self, text: str) -> str:
        """Добавить безопасный пример"""
        doc_id = self.vector_store.add_white_example(text)
        if doc_id:
            logger.info(f"➕ Добавлен безопасный пример: {text[:50]}...")
        return doc_id
    
    def add_black_example(self, text: str) -> str:
        """Добавить рекламный пример"""
        doc_id = self.vector_store.add_black_example(text)
        if doc_id:
            logger.info(f"➕ Добавлен рекламный пример: {text[:50]}...")
        return doc_id
    
    def delete_white_by_text(self, text: str) -> Tuple[int, List[str]]:
        """Удалить безопасные примеры"""
        count, texts = self.vector_store.delete_white_by_text(text)
        return count, texts
    
    def delete_black_by_text(self, text: str) -> Tuple[int, List[str]]:
        """Удалить рекламные примеры"""
        count, texts = self.vector_store.delete_black_by_text(text)
        return count, texts
    
    def find_white_by_text(self, text: str) -> List[Dict]:
        """Найти безопасные примеры"""
        return self.vector_store.find_by_text_white(text)
    
    def find_black_by_text(self, text: str) -> List[Dict]:
        """Найти рекламные примеры"""
        return self.vector_store.find_by_text_black(text)
    
    def list_white_examples(self, limit: int = 20) -> List[Dict]:
        """Список безопасных примеров"""
        return self.vector_store.list_all_examples(self.vector_store.white_collection, limit)
    
    def list_black_examples(self, limit: int = 20) -> List[Dict]:
        """Список рекламных примеров"""
        return self.vector_store.list_all_examples(self.vector_store.black_collection, limit)
    
    def get_statistics(self) -> dict:
        """Получить статистику"""
        return self.vector_store.get_stats()
ragservice = RAGService()