import chromadb
from chromadb.config import Settings
from typing import List, Tuple, Optional, Dict
import uuid
from datetime import datetime
import os
import numpy as np
import logging
logger = logging.getLogger(__name__)
class VectorStore:
    def __init__(self):
        self.persist_directory = "./chroma_db"
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.white_collection = self._get_or_create_collection("safe_messages")
        self.black_collection = self._get_or_create_collection("advertisements")
        
        if self.white_collection.count() == 0:
            self._add_base_white_examples()
        
        if self.black_collection.count() == 0:
            self._add_base_black_examples()
    
    def _get_or_create_collection(self, name: str):
        """Получить или создать коллекцию"""
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def _add_base_white_examples(self):
        """Базовые безопасные сообщения"""
        safe_examples = [
            "Привет, как дела?",
            "Здравствуйте, чем занимаетесь?",
            "Добрый день, всем привет",
            "Ребята, кто сегодня будет?",
            "Спасибо большое за помощь",
            "Пожалуйста, помогите мне",
            "Как у вас проходит день?",
            "Отличная погода сегодня",
            "Кто знает, как это сделать?",
            "Извините, я не понял вопрос",
            "Хорошо, договорились",
            "Давайте обсудим это позже",
            "Согласен с вами полностью",
            "Интересная мысль, спасибо",
            "Ничего страшного, бывает"
        ]
        
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embeddings = model.get_embeddings_batch(safe_examples)
        
        ids = [str(uuid.uuid4()) for _ in safe_examples]
        metadatas = [
            {"type": "safe", "added": datetime.now().isoformat()}
            for _ in safe_examples
        ]
        
        self.white_collection.add(
            embeddings=embeddings,
            documents=safe_examples,
            metadatas=metadatas,
            ids=ids
        )
        logger.debug(f"✅ Добавлено {len(safe_examples)} безопасных примеров")
    
    def _add_base_black_examples(self):
        """Базовые рекламные сообщения"""
        ad_examples = [
            "Срочно ищу 3 человека оплата от 5к подробности в л",
            "СРОЧНО! 6 человек на шабашку, плачу наличкой",
            "Купите наш товар со скидкой 50%",
            "Переходите по ссылке и получайте бонусы",
            "Оставьте заявку и получите консультацию бесплатно",
            "Подпишитесь на канал и получите подарок",
            "Зарабатывайте от 1000$ в день, подробности по ссылке",
            "Срочно! Работа для студентов, звоните 8-800",
            "Онлайн-курсы, скидка на обучение 40% по промокоду",
            "Переходи в Telegram канал для бонусов",
            "Успей купить со скидкой, осталось 2 дня",
            "Звони прямо сейчас, первая консультация бесплатно",
            "Регистрируйся и получай 1000 рублей на счет",
            "Скидки до 80% только сегодня в нашем магазине",
            "Оставь заявку и получи индивидуальный расчет"
        ]
        
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embeddings = model.get_embeddings_batch(ad_examples)
        
        ids = [str(uuid.uuid4()) for _ in ad_examples]
        metadatas = [
            {"type": "spam", "added": datetime.now().isoformat()}
            for _ in ad_examples
        ]
        
        self.black_collection.add(
            embeddings=embeddings,
            documents=ad_examples,
            metadatas=metadatas,
            ids=ids
        )
        logger.debug(f"✅ Добавлено {len(ad_examples)} рекламных примеров")
    
    def add_white_example(self, text: str, metadata: dict = None) -> str:
        """Добавить безопасное сообщение"""
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embedding = model.get_embedding(text)
        
        if embedding is None:
            return None
            
        doc_id = str(uuid.uuid4())
        metadata = metadata or {}
        metadata.update({
            "type": "safe",
            "added": datetime.now().isoformat()
        })
        
        self.white_collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        return doc_id
    
    def add_black_example(self, text: str, metadata: dict = None) -> str:
        """Добавить рекламное сообщение"""
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embedding = model.get_embedding(text)
        
        if embedding is None:
            return None
            
        doc_id = str(uuid.uuid4())
        metadata = metadata or {}
        metadata.update({
            "type": "spam",
            "added": datetime.now().isoformat()
        })
        
        self.black_collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        return doc_id
    
    def get_similar(self, text: str, collection, n_results: int = 5) -> Dict:
        """Получить похожие документы из коллекции"""
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embedding = model.get_embedding(text)
        
        if embedding is None:
            return {"documents": [[]], "distances": [[]], "metadatas": [[]]}
        
        return collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "distances", "metadatas"]
        )
    
    def classify_text_advanced(self, text: str, top_k: int = 5) -> Dict:
        """Классификация текста через RAG"""
        # 1. Получаем похожие из обеих коллекций
        white_results = self.get_similar(text, self.white_collection, top_k)
        black_results = self.get_similar(text, self.black_collection, top_k)
        
        white_docs = white_results['documents'][0] if white_results['documents'] else []
        white_dists = white_results['distances'][0] if white_results['distances'] else []
        white_metas = white_results['metadatas'][0] if white_results['metadatas'] else []
        
        black_docs = black_results['documents'][0] if black_results['documents'] else []
        black_dists = black_results['distances'][0] if black_results['distances'] else []
        black_metas = black_results['metadatas'][0] if black_results['metadatas'] else []
        
        # 2. Вычисляем сходство
        safe_scores = [1 - dist for dist in white_dists] if white_dists else [0.0]
        spam_scores = [1 - dist for dist in black_dists] if black_dists else [0.0]
        
        max_safe = max(safe_scores) if safe_scores else 0.0
        max_spam = max(spam_scores) if spam_scores else 0.0
        
        # 3. Проверяем наличие рекламных примеров с высоким сходством
        SPAM_THRESHOLD = 0.4
        SAFE_THRESHOLD = 0.6
        
        high_spam_exists = any(score > SPAM_THRESHOLD for score in spam_scores)
        high_safe_exists = any(score > SAFE_THRESHOLD for score in safe_scores)
        
        # 4. Логика принятия решений
        if high_spam_exists:
            if max_safe > max_spam and max_safe > SAFE_THRESHOLD:
                return {
                    "is_ad": False,
                    "score": max_safe,
                    "method": "safe_dominates",
                    "delta": max_safe - max_spam,
                    "closest_white": white_docs[0] if white_docs else None,
                    "closest_black": black_docs[0] if black_docs else None
                }
            else:
                return {
                    "is_ad": True,
                    "score": max_spam,
                    "method": "spam_detected",
                    "delta": max_spam - max_safe if max_spam > max_safe else 0,
                    "closest_white": white_docs[0] if white_docs else None,
                    "closest_black": black_docs[0] if black_docs else None
                }
        else:
            if high_safe_exists:
                return {
                    "is_ad": False,
                    "score": max_safe,
                    "method": "safe_detected",
                    "delta": 0,
                    "closest_white": white_docs[0] if white_docs else None,
                    "closest_black": None
                }
            else:
                return {
                    "is_ad": False,
                    "score": 0.0,
                    "method": "no_match",
                    "delta": 0,
                    "closest_white": None,
                    "closest_black": None
                }
    
    def find_by_text(self, collection, text: str, threshold: float = 0.1) -> List[Dict]:
        """Найти документы по тексту"""
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embedding = model.get_embedding(text)
        
        if embedding is None:
            return []
        
        results = collection.query(
            query_embeddings=[embedding],
            n_results=10,
            include=["documents", "distances", "metadatas"]
        )
        
        matches = []
        if results['documents'] and results['documents'][0]:
            for doc, dist, meta in zip(
                results['documents'][0],
                results['distances'][0],
                results['metadatas'][0]
            ):
                if dist <= threshold:
                    matches.append({
                        "id": results['ids'][0][results['documents'][0].index(doc)],
                        "text": doc,
                        "distance": dist,
                        "metadata": meta
                    })
        
        return matches
    
    def delete_by_text(self, collection, text: str, threshold: float = 0.1) -> Tuple[int, List[str]]:
        """Удалить документы по тексту"""
        matches = self.find_by_text(collection, text, threshold)
        
        if not matches:
            return 0, []
        
        ids_to_delete = [m['id'] for m in matches]
        texts_deleted = [m['text'] for m in matches]
        
        collection.delete(ids=ids_to_delete)
        
        return len(ids_to_delete), texts_deleted
    
    def find_by_text_white(self, text: str, threshold: float = 0.1) -> List[Dict]:
        """Найти в белой коллекции"""
        return self.find_by_text(self.white_collection, text, threshold)
    
    def find_by_text_black(self, text: str, threshold: float = 0.1) -> List[Dict]:
        """Найти в черной коллекции"""
        return self.find_by_text(self.black_collection, text, threshold)
    
    def delete_white_by_text(self, text: str, threshold: float = 0.1) -> Tuple[int, List[str]]:
        """Удалить из белой коллекции по тексту"""
        return self.delete_by_text(self.white_collection, text, threshold)
    
    def delete_black_by_text(self, text: str, threshold: float = 0.1) -> Tuple[int, List[str]]:
        """Удалить из черной коллекции по тексту"""
        return self.delete_by_text(self.black_collection, text, threshold)
    
    def list_all_examples(self, collection, limit: int = 20) -> List[Dict]:
        """Получить список всех примеров"""
        results = collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )
        
        examples = []
        if results['ids']:
            for idx, doc_id in enumerate(results['ids']):
                examples.append({
                    "id": doc_id,
                    "text": results['documents'][idx] if idx < len(results['documents']) else "",
                    "metadata": results['metadatas'][idx] if idx < len(results['metadatas']) else {}
                })
        
        return examples
    
    def get_stats(self) -> dict:
        """Статистика по обеим коллекциям"""
        return {
            "white_count": self.white_collection.count(),
            "black_count": self.black_collection.count(),
            "total": self.white_collection.count() + self.black_collection.count()
        }