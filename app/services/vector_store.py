import chromadb
from chromadb.config import Settings
from typing import List, Tuple, Optional, Dict
import uuid
from datetime import datetime
import os
import numpy as np

class VectorStore:
    def __init__(self):
        self.persist_directory = "./chroma_db"
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # ДВЕ КОЛЛЕКЦИИ: белая и черная
        self.white_collection = self._get_or_create_collection("safe_messages")
        self.black_collection = self._get_or_create_collection("advertisements")
        
        # Проверяем, пустые ли коллекции
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
        """Базовые безопасные сообщения (НЕ реклама)"""
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
            "Ничего страшного, бывает",
            "Ребят, а кто в курсе?",
            "Может быть, стоит попробовать",
            "Не знаю, что сказать",
            "Всем хорошего настроения!",
            "Какой у вас график работы?"
        ]
        
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embeddings = model.get_embeddings_batch(safe_examples)
        
        ids = [str(uuid.uuid4()) for _ in safe_examples]
        metadatas = [
            {"type": "base_white", "added": datetime.now().isoformat()}
            for _ in safe_examples
        ]
        
        self.white_collection.add(
            embeddings=embeddings,
            documents=safe_examples,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Добавлено {len(safe_examples)} безопасных примеров")
    
    def _add_base_black_examples(self):
        """Базовые рекламные сообщения"""
        ad_examples = [
            "Купите наш товар со скидкой 50%",
            "Переходите по ссылке и получайте бонусы",
            "Лучшие условия на рынке, звоните сейчас",
            "Скидки до 80% только сегодня",
            "Оставьте заявку и получите консультацию бесплатно",
            "Узнайте свой заработок за 5 минут",
            "Подпишитесь на канал и получите подарок",
            "Перейдите по ссылке в описании",
            "Покупайте в нашем магазине с кешбэком",
            "Регистрируйтесь по ссылке и получайте приветственный бонус",
            "Зарабатывайте от 1000$ в день, подробности по ссылке",
            "Срочно! Работа для студентов, звоните 8-800",
            "Онлайн-курсы, скидка на обучение 40% по промокоду",
            "Только сегодня! Успейте купить со скидкой",
            "Переходите в Telegram канал для бонусов"
        ]
        
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embeddings = model.get_embeddings_batch(ad_examples)
        
        ids = [str(uuid.uuid4()) for _ in ad_examples]
        metadatas = [
            {"type": "base_black", "added": datetime.now().isoformat()}
            for _ in ad_examples
        ]
        
        self.black_collection.add(
            embeddings=embeddings,
            documents=ad_examples,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Добавлено {len(ad_examples)} рекламных примеров")
    
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
            "type": "user_white",
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
            "type": "user_black",
            "added": datetime.now().isoformat()
        })
        
        self.black_collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        return doc_id
    
    def classify_text(self, text: str, top_k: int = 3) -> Dict:
        """
        Классифицирует текст: реклама или нет
        """
        from .model_loader import EmbeddingModel
        model = EmbeddingModel()
        embedding = model.get_embedding(text)
        
        if embedding is None:
            return {
                "is_ad": False,
                "score": 0.0,
                "closest_white": None,
                "closest_black": None,
                "white_distances": [],
                "black_distances": []
            }
        
        # Ищем в БЕЛОЙ коллекции
        white_results = self.white_collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )
        
        # Ищем в ЧЕРНОЙ коллекции
        black_results = self.black_collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )
        
        white_distances = white_results['distances'][0] if white_results['distances'] else []
        black_distances = black_results['distances'][0] if black_results['distances'] else []
        
        if not white_distances and not black_distances:
            return {
                "is_ad": False,
                "score": 0.0,
                "closest_white": None,
                "closest_black": None,
                "white_distances": [],
                "black_distances": []
            }
        
        # Используем МИНИМАЛЬНЫЕ расстояния (самые похожие)
        min_white_dist = min(white_distances) if white_distances else float('inf')
        min_black_dist = min(black_distances) if black_distances else float('inf')
        
        # Логика классификации
        is_ad = False
        score = 0.0
        
        # Если есть только один тип примеров
        if min_white_dist == float('inf') and min_black_dist == float('inf'):
            is_ad = False
            score = 0.0
        elif min_white_dist == float('inf'):
            is_ad = True
            score = 1 - min_black_dist
        elif min_black_dist == float('inf'):
            is_ad = False
            score = 1 - min_white_dist
        else:
            # ОСНОВНАЯ ЛОГИКА: сравниваем расстояния
            # Если черный пример ближе - реклама
            if min_black_dist < min_white_dist:
                is_ad = True
                score = 1 - min_black_dist
            # Если белый пример ближе - НЕ реклама
            else:
                is_ad = False
                score = 1 - min_white_dist
            
            # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: если черный пример очень похож (distance < 0.5)
            # даже если белый немного ближе - все равно реклама
            if min_black_dist < 0.5 and min_black_dist < min_white_dist * 1.2:
                is_ad = True
                score = 1 - min_black_dist
            
            # Если оба расстояния большие (> 0.7) - считаем безопасным
            if min_white_dist > 0.7 and min_black_dist > 0.7:
                is_ad = False
                score = max(0, 1 - min_white_dist)
        
        return {
            "is_ad": is_ad,
            "score": score,
            "closest_white": white_results['documents'][0][0] if white_results['documents'] else None,
            "closest_black": black_results['documents'][0][0] if black_results['documents'] else None,
            "white_distances": white_distances,
            "black_distances": black_distances,
            "min_white_dist": min_white_dist,
            "min_black_dist": min_black_dist
        }
    def get_stats(self) -> dict:
        """Статистика по обеим коллекциям"""
        return {
            "white_count": self.white_collection.count(),
            "black_count": self.black_collection.count(),
            "total": self.white_collection.count() + self.black_collection.count()
        }
    def query(self, text: str):
        white_results = self.white_collection.query(
            query_texts=[text],
            n_results=1
        )
        
        # Ищем в ЧЕРНОЙ коллекции
        black_results = self.black_collection.query(
            query_texts=[text],
            n_results=1
        )
        if white_results['ids'] and white_results['ids'][0]:
            return white_results['ids'][0][0]
        elif black_results['ids'] and black_results['ids'][0]:
            return black_results['ids'][0][0]
    def remove(self, text: str):
        white_results = self.white_collection.query(
            query_texts=[text],
            n_results=1
        )
        
        # Ищем в ЧЕРНОЙ коллекции
        black_results = self.black_collection.query(
            query_texts=[text],
            n_results=1
        )
        if white_results['ids'] and white_results['ids'][0]:
            self.white_collection.delete(white_results['ids'][0][0])
        elif black_results['ids'] and black_results['ids'][0]:
             self.black_collection.delete(black_results['ids'][0][0])