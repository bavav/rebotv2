from aiogram.filters import BaseFilter
from aiogram.types import Message
from shared.app.config import settings
from shared.app.logger import configure_logging, get_logger
from ..config import config
from ..services.cascade import cascade
from typing import Dict,Any
from ..services.ml_errors import CheckedText, get_sesion
configure_logging(settings.log_level)
logger = get_logger(__name__)

class MainFilter():
    def __init__(self):
        self.cascade_classifier = cascade
        
    
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
        logger.debug("kokokok")
        res = self.cascade_classifier.predict(text)
        with get_sesion() as session:
            
            new_text = CheckedText(text=text,from_user_id=message.from_user.id,message_id=message.message_id,chat_id = message.chat.id,is_spam = res.is_spam,reason=res.reason,confidence=res.confidence)
            session.add(new_text)
            session.commit()  
        logger.info("ml_res",body={"reason":res.reason,"confidense":res.proba,"is_spam":res.is_spam})
        if res.is_spam:
            return True
        return False
        