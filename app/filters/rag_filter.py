from aiogram.filters import BaseFilter
from aiogram.types import Message
import logging
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class RagFilter(BaseFilter):
    def __init__(self):
        self.rag_service = RAGService()
    
    async def __call__(self, message: Message) -> bool:
        # Проверяем наличие текста
        print("wrk")
        if not message.text:
            print("kaak?")
            return False
        
        text = message.text.strip()
        
        # Пропускаем команды
        if text.startswith('/'):
            return False
        
        # Пропускаем слишком короткие сообщения (меньше 3 слов)
        if len(text.split()) < 3:
            logger.debug(f"🟢 Слишком короткое сообщение: {text}")
            return False
        
        # Основная проверка через RAG
        is_ad, confidence, closest_white, closest_black = self.rag_service.check_advertisement(text)
        
        return is_ad