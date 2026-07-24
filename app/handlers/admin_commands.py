from aiogram import Router, types
from aiogram.filters import Command
from app.services.rag_service import RAGService
import logging

logger = logging.getLogger(__name__)
router = Router()
rag_service = RAGService()
from app.config import config
@router.message(Command("add_white"))
async def add_white_example(message: types.Message):
    """Добавить безопасный пример (НЕ реклама)"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/add_white", "").strip()
    
    if not text:
        # Если ответили на сообщение
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /add_white [текст]\n"
                "Или ответьте на сообщение"
            )
            return
    
    doc_id = rag_service.add_white_example(text)
    
    await message.reply(
        f"✅ Безопасный пример добавлен!\n"
        f"📝 ID: {doc_id[:8]}...\n"
        f"📊 Всего примеров: {rag_service.get_statistics()}"
    )

@router.message(Command("add_black"))
async def add_black_example(message: types.Message):
    """Добавить рекламный пример"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/add_black", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /add_black [текст]\n"
                "Или ответьте на сообщение"
            )
            return
    
    doc_id = rag_service.add_black_example(text)
    
    await message.reply(
        f"✅ Рекламный пример добавлен!\n"
        f"📝 ID: {doc_id[:8]}...\n"
        f"📊 Всего примеров: {rag_service.get_statistics()}"
    )
@router.message(Command("get_id"))
async def getid(message: types.Message):
    """Добавить рекламный пример"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/get_id", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /get [текст]\n"
                "Или ответьте на сообщение"
            )
            return
    
    doc_id = rag_service.query(text)
    
    await message.reply(
       f"id: {doc_id}"
    )
@router.message(Command("stats"))
async def get_stats(message: types.Message):
    """Показать статистику"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    stats = rag_service.get_statistics()
    
    text = (
        f"📊 Статистика RAG-фильтра:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🟢 Безопасных: {stats['white_count']}\n"
        f"🔴 Рекламных: {stats['black_count']}\n"
        f"📚 Всего: {stats['total']}\n"
        f"🎯 Мин. уверенность: {stats['min_confidence']:.2f}"
    )
    
    await message.reply(text)
@router.message(Command("check_id"))
async def check_id(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
@router.message(Command("check"))
async def check_text(message: types.Message):
    """Проверить текст (подробный вывод)"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/check", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply("ℹ️ Используйте: /check [текст]")
            return
    
    is_ad, confidence, closest_white, closest_black = rag_service.check_advertisement(text)
    
    result_text = (
        f"🔍 Результат проверки:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 Текст: {text[:50]}...\n"
        f"{'🔴 РЕКЛАМА' if is_ad else '🟢 НЕ РЕКЛАМА'}\n"
        f"📊 Уверенность: {confidence:.2f}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🟢 Ближайший безопасный:\n{closest_white[:50] if closest_white else 'Нет'}\n"
        f"🔴 Ближайший рекламный:\n{closest_black[:50] if closest_black else 'Нет'}"
    )
    
    await message.reply(result_text)

@router.message(Command("set_confidence"))
async def set_confidence(message: types.Message):
    """Установить порог уверенности"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError
        new_confidence = float(parts[1])
        
        if not (0 < new_confidence < 1):
            await message.reply("❌ Значение должно быть между 0 и 1")
            return
        
        rag_service.set_confidence(new_confidence)
        await message.reply(f"✅ Порог уверенности изменен на {new_confidence:.2f}")
        
    except (ValueError, IndexError):
        await message.reply(
            "❌ Неверный формат\n"
            "Используйте: /set_confidence 0.3"
        )