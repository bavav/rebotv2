from sentence_transformers import SentenceTransformer, util
import torch
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class SpamClassifier:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.threshold = 0.5
        self.model_name = 'ruSpamModels/ruSpam_big'
        
        self.model = None
        self.load_model(self.model_name)
        
        # Шаблоны для сравнения
        self.spam_template = "спам реклама предложение услуга скидка акция"
        self.safe_template = "привет как дела хороший день нормальное общение"
        
        self.spam_embedding = None
        self.safe_embedding = None
        self._update_template_embeddings()
        
        logger.info(f"✅ ML-классификатор инициализирован на {self.device}")
    
    def load_model(self, model_name: str) -> bool:
        """Загрузить модель по имени"""
        try:
            if self.model is not None:
                del self.model
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            logger.info(f"🔄 Загрузка модели: {model_name}")
            self.model = SentenceTransformer(model_name, device=self.device)
            self.model_name = model_name
            self._update_template_embeddings()
            logger.info(f"✅ Модель загружена: {model_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели {model_name}: {e}")
            if model_name != 'ruSpamModels/ruSpam_big':
                try:
                    logger.info("🔄 Пробуем загрузить модель по умолчанию...")
                    self.model = SentenceTransformer('ruSpamModels/ruSpam_big', device=self.device)
                    self.model_name = 'ruSpamModels/ruSpam_big'
                    self._update_template_embeddings()
                    logger.info("✅ Модель по умолчанию загружена")
                    return True
                except:
                    pass
            return False
    
    def _update_template_embeddings(self):
        """Обновить эмбеддинги шаблонов"""
        if self.model is None:
            return
        
        self.spam_embedding = self.model.encode(
            self.spam_template,
            convert_to_tensor=True,
            normalize_embeddings=True
        )
        self.safe_embedding = self.model.encode(
            self.safe_template,
            convert_to_tensor=True,
            normalize_embeddings=True
        )
    
    def set_threshold(self, threshold: float):
        """Установить порог уверенности"""
        if 0 <= threshold <= 1:
            self.threshold = threshold
            logger.info(f"📊 Порог модели изменен: {threshold}")
    
    def set_templates(self, spam_text: str, safe_text: str):
        """Изменить шаблоны для сравнения"""
        self.spam_template = spam_text
        self.safe_template = safe_text
        self._update_template_embeddings()
        logger.info("🔄 Шаблоны обновлены")
    
    def predict(self, text: str) -> Tuple[bool, float]:
        """Предсказать, является ли текст спамом"""
        if not text or len(text.strip()) == 0:
            return False, 0.0
        
        if self.model is None:
            logger.warning("⚠️ Модель не загружена, пропускаем проверку")
            return False, 0.0
        
        try:
            text_embedding = self.model.encode(
                text,
                convert_to_tensor=True,
                normalize_embeddings=True
            )
            
            spam_similarity = util.cos_sim(text_embedding, self.spam_embedding)
            safe_similarity = util.cos_sim(text_embedding, self.safe_embedding)
            
            spam_score = float(spam_similarity)
            safe_score = float(safe_similarity)
            
            if spam_score > 0.1 or safe_score > 0.1:
                confidence = spam_score / (spam_score + safe_score + 0.001)
            else:
                confidence = 0.0
            
            confidence = max(0.0, min(1.0, confidence))
            is_spam = confidence > self.threshold
            
            return is_spam, confidence
            
        except Exception as e:
            logger.error(f"❌ Ошибка в ML-модели: {e}")
            return False, 0.0
    
    def get_available_models(self) -> list:
        """Получить список доступных моделей"""
        return [
            'ruSpamModels/ruSpam_big',
            'ruSpamModels/ruSpam_small',
            'cointegrated/rubert-tiny-toxicity',
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        ]