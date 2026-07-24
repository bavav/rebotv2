from sentence_transformers import SentenceTransformer
import torch

class EmbeddingModel:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Используем легкую русскую модель для эмбеддингов
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        print(f"✅ Модель загружена на {self.device}")
    
    def get_embedding(self, text: str) -> list:
        """Получить векторное представление текста"""
        if not text or len(text.strip()) == 0:
            return None
            
        # Для модели e5 нужно добавлять префикс
        # 'query: ' для поиска, 'passage: ' для индексации
        embeddings = self.model.encode(
            f"query: {text}",
            normalize_embeddings=True  # Нормализация для косинусного сходства
        )
        return embeddings.tolist()
    
    def get_embeddings_batch(self, texts: list) -> list:
        """Получить векторы для списка текстов"""
        if not texts:
            return []
        
        # Добавляем префикс для всех текстов
        prefixed_texts = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(
            prefixed_texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return [emb.tolist() for emb in embeddings]