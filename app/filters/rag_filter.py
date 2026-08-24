from aiogram.filters import BaseFilter
from aiogram.types import Message
import logging
from app.services.rag_service import ragservice
from app.config import config
from typing import Dict,Any
logger = logging.getLogger(__name__)

class RagFilter(BaseFilter):
    def __init__(self):
        self.rag_service = ragservice
    
    async def __call__(self, message: Message,**kwargs) -> bool:
        if not message.text:
            return False
        if message.chat.id not in config.CHATS_IDS:
            return False
        text = message.text.strip()
        user_data: Dict[str, Any] = kwargs.get("user_data", {})
        message_count = user_data.get("message_count")
        # Пропускаем команды
        if text.startswith('/'):
            return False
        
        # Слишком короткие сообщения пропускаем
        if len(text.split()) < 3:
            return False
        
        # Проверка через RAG + ML
        is_ad, confidence, method, closest_white, closest_black = self.rag_service.check_advertisement(text,message_count=message_count)
        
        if is_ad:
            logger.info(f"🔴 РЕКЛАМА | Метод: {method} | Уверенность: {confidence:.2f} | Текст: {text[:50]}...")
        
        return is_ad