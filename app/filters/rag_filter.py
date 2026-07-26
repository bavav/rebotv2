from aiogram.filters import BaseFilter
from aiogram.types import Message
import logging
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class RagFilter(BaseFilter):
    def __init__(self):
        self.rag_service = RAGService()
    
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        
        text = message.text.strip()
        
        # Пропускаем команды
        if text.startswith('/'):
            return False
        
        # Слишком короткие сообщения пропускаем
        if len(text.split()) < 3:
            return False
        
        # Проверка через RAG + ML
        is_ad, confidence, method, closest_white, closest_black = self.rag_service.check_advertisement(text)
        
        if is_ad:
            logger.info(f"🔴 РЕКЛАМА | Метод: {method} | Уверенность: {confidence:.2f} | Текст: {text[:50]}...")
        
        return is_ad