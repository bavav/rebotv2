from typing import Tuple, Optional, Dict, List
import logging
from .vector_store import VectorStore
from .ml_model import SpamClassifier

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
        self.ml_classifier = SpamClassifier()
        self.use_ml = True
        logger.info("✅ RAG Service инициализирован с ML-поддержкой")
    
    def check_advertisement(self, text: str) -> Tuple[bool, float, str, Optional[str], Optional[str]]:
        """Проверка рекламы: RAG + ML"""
        # ЭТАП 1: RAG-проверка
        rag_result = self.vector_store.classify_text_advanced(text)
        
        if rag_result['is_ad']:
            return True, rag_result['score'], f"rag_{rag_result['method']}", rag_result.get('closest_white'), rag_result.get('closest_black')
        
        # ЭТАП 2: ML-проверка
        if self.use_ml:
            is_spam, ml_confidence = self.ml_classifier.predict(text)
            
            if is_spam:
                logger.info(f"🤖 ML обнаружил рекламу: {text[:50]}... (Уверенность: {ml_confidence:.2f})")
                return True, ml_confidence, "ml_classifier", rag_result.get('closest_white'), rag_result.get('closest_black')
        
        return False, rag_result['score'], f"rag_{rag_result['method']}", rag_result.get('closest_white'), rag_result.get('closest_black')
    
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