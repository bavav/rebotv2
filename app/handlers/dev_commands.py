from datetime import timedelta
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


from ...app.config import config
import logging
from ...app.services.cascade import cascade
logger = logging.getLogger(__name__)
router = Router()
rag_service = "ragservice"
ml_classifier = "ragservice.ml_classifier"
import uuid
from cachetools import TTLCache

from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup

# Фабрика для кнопок главного меню (мут/бан)
from ads_worker.app.admin_module.handlers.comands import rout,F

# Временное хранилище: token -> текст для удаления.
# TTL = 10 минут, максимум 1000 записей.
_pending_deletes: TTLCache = TTLCache(maxsize=1000, ttl=600)


def _register_delete(text: str) -> str:
    """Регистрирует текст и возвращает короткий токен (16 hex-символов)."""
    token = uuid.uuid4().hex[:16]
    _pending_deletes[token] = text
    return token







@rout.event("message",F.text.startswith("/toggle_ml"))
async def toggle_ml(message: types.Message):
    """Включить/выключить ML-проверку"""
    if message.from_user.id not in config.get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    rag_service.use_ml = not rag_service.use_ml
    status = "✅ ВКЛЮЧЕНА" if rag_service.use_ml else "❌ ВЫКЛЮЧЕНА"
    
    await message.reply(
        f"🔄 ML-проверка: {status}\n"
        f"ℹ️ RAG-проверка всегда активна"
    )


# ==================== ПРОВЕРКА И СТАТИСТИКА ====================

@rout.event("message",F.text.startswith("/check"))
async def check_text(message: types.Message):
    """Проверить текст с подробным выводом"""
    if message.from_user.id not in config.get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/check", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply("ℹ️ Используйте: /check [текст]")
            return
    
    
    res = cascade.predict(text)
    
    method_emoji = {
        "cascade_logreg_spam": "⚡",
        "cascade_gbm_spam": "⚡",
        "cascade_gbm_safe": "🟢",
        "cascade_logreg_safe": "🟢",
        "cascade_svm": "🧠"
    }.get(res.reason, "❓")
    
    result_text = (
        f"🔍 Результат проверки:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 Текст: {text[:50]}...\n"
        f"{'🔴 РЕКЛАМА' if res.is_spam else '🟢 НЕ РЕКЛАМА'}\n"
        f"📊 Уверенность: {res.confidence:.2f}\n"
        f"🔬 Метод: {method_emoji} {res.reason}\n"
        )
    
    await message.reply(result_text)


@rout.event("message",F.text.startswith("/stats"))
async def get_stats(message: types.Message):
    """Показать общую статистику"""
    if message.from_user.id not in config.get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    from ..services.ml_errors import CheckedText,get_sesion
    
    from sqlalchemy import select
    with get_sesion() as session:
        statement = select(CheckedText).where(CheckedText.ts_of_getting > datetime.now() - timedelta(weeks=1))
        texts = session.scalars(statement).all()
        q,w,e = 0,0,0
        for i in texts:
            if i.approwed_is_spam == True:
                q +=1
            elif i.approwed_is_spam == False:
                w += 1
            else:
                e +=1
            total_verified = q + w

            if total_verified > 0:
                # Рассчитываем проценты (округляем до 1 знака после запятой)
                hit_rate = round((q / total_verified) * 100, 1)
                miss_rate = round((w / total_verified) * 100, 1)
                
                stats_accuracy = f"🎯 Точность ИИ (попадания): {hit_rate}%\n"
                stats_accuracy += f"❌ Ошибки ИИ (промахи): {miss_rate}%\n"
            else:
                stats_accuracy = "📊 Точность ИИ: Админ пока не проверил ни одного текста.\n"

                
        n = ""
        n += "Всего 'спам' текстов за последнюю неделю: "+ str(len(texts)) + "\n"
        n += f"Помечено как 'не спам' админом: {w}\n"
        n += f"Помечено как 'спам' админом: {q}\n"
        n += f"Не проверено админом: {e}\n"
        n += "━━━━━━━━━━━━━━━━\n"
        n += stats_accuracy
        
        print(n)
        
    await message.reply(
        f"📊 Общая статистика:\n"
        f"━━━━━━━━━━━━━━━━\n"+
        n
    )





    