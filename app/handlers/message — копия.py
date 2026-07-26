from aiogram import Router, types
from app.config import config
from app.filters.rag_filter import RagFilter
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(RagFilter())
async def forward_filtered_message(message: types.Message):
    """Пересылает сообщение, если фильтр сработал"""
    try:
        # Пересылаем целевому пользователю
        await message.forward(chat_id=config.TARGET_USER_ID)
        logger.info(f"📤 Переслано сообщение: {message.text[:50]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка пересылки: {e}")