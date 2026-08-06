from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.services.rag_service import RAGService
from app.services.ml_model import SpamClassifier
from app.config import config
import logging
from modules_loader import IsModuleActive

logger = logging.getLogger("admin_module"+ __name__)
router = Router()
rag_service = RAGService()
ml_classifier = SpamClassifier()

@router.message(Command("add_admin"),IsModuleActive("admin"))
async def set_ml_threshold(message: types.Message):
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    text = message.text.replace("/add_admin", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /add_admin [id],(id),(id)...\n"
                "Или ответьте на сообщение, того кого нужно добавить, этой командой"
            )
            return
    
    config.add_admin([map(int,text.split())])
    logger.info("Добавлены админы с id: "+ text)