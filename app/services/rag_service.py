from typing import Tuple, Optional, Dict
import logging
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

class RAGService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.vector_store = VectorStore()
        self.min_confidence = 0.3  # Минимальная уверенность для определения
        logger.info("✅ RAG Service инициализирован с двойной базой")
    def query(self, text: str):
        return self.vector_store.query(text)
    def check_advertisement(self, text: str) -> Tuple[bool, float, Optional[str], Optional[str]]:
        """
        Проверяет, является ли текст рекламным
        
        Returns:
            (is_ad: bool, confidence: float, closest_white: str, closest_black: str)
        """
        # Классифицируем текст
        result = self.vector_store.classify_text(text)
        
        is_ad = result['is_ad']
        confidence = result['score']
        
        # Если уверенность низкая, считаем безопасным
        if confidence < self.min_confidence:
            is_ad = False
        logger.info(
                f"🔴 РЕКЛАМА: {text[:50]}... "
                f"(Уверенность: {confidence:.2f}, "
                f"Черный: {result['closest_black'][:30] if result['closest_black'] else 'None'})"
                f"ad: {is_ad}"
            )
        # Логируем результат
        if is_ad:
            logger.info(
                f"🔴 РЕКЛАМА: {text[:50]}... "
                f"(Уверенность: {confidence:.2f}, "
                f"Черный: {result['closest_black'][:30] if result['closest_black'] else 'None'})"
            )
        else:
            logger.info(
                f"🟢 БЕЗОПАСНО: {text[:50]}... "
                f"(Уверенность: {confidence:.2f}, "
                f"Белый: {result['closest_white'][:30] if result['closest_white'] else 'None'})"
            )
        
        return is_ad, confidence, result['closest_white'], result['closest_black']
    
    def add_white_example(self, text: str) -> str:
        """Добавить безопасный пример"""
        doc_id = self.vector_store.add_white_example(text)
        logger.info(f"➕ Добавлен безопасный пример: {text[:50]}...")
        return doc_id
    
    def add_black_example(self, text: str) -> str:
        """Добавить рекламный пример"""
        doc_id = self.vector_store.add_black_example(text)
        logger.info(f"➕ Добавлен рекламный пример: {text[:50]}...")
        return doc_id
    
    def get_statistics(self) -> dict:
        """Получить статистику"""
        stats = self.vector_store.get_stats()
        stats['min_confidence'] = self.min_confidence
        return stats
    
    def set_confidence(self, new_confidence: float):
        """Изменить порог уверенности"""
        if 0 < new_confidence < 1:
            self.min_confidence = new_confidence
            logger.info(f"Порог уверенности изменен на {new_confidence}")