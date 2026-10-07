# message.py - альтернативный вариант с кнопками на пересланном сообщении
from datetime import datetime
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ...app.config import config
from ..filters.main_filter import MainFilter
from aiogram.enums import ParseMode
import logging
from ...storage import add_globan_data
logger = logging.getLogger(__name__)
router = Router()
from ..services.ml_errors import CheckedText, get_sesion
from sqlalchemy import select
# Словарь для хранения текстов сообщений
pending_messages = {}
from ads_worker.app.admin_module.handlers.comands import rout,F
@rout.event("message",MainFilter())
async def forward_filtered_message(message: types.Message):
    """Пересылает сообщение с кнопками для добавления в белый/черный список"""
    logger.debug("f: "+str(config.ADMIN_IDS.keys())+" "+str(message.chat.id))
    try:
        # Получаем текст сообщения
        text = message.text or message.caption or ""
        
        
        
       
        with get_sesion() as session:
            statement = select(CheckedText).where(CheckedText.text == text)
            msg = session.scalars(statement).first()
        
        key = msg.id
        
        for user in config.ADMIN_IDS[message.chat.id]:
            forwarded = await message.forward(chat_id=user)
            
            # Создаем кнопки для действий
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                
                [
                    InlineKeyboardButton(
                        text="⏭ Пропустить", 
                        callback_data=f"action_skip_{msg.id}"
                    ),
                    InlineKeyboardButton(
                        text="🚫 Глобан", 
                        callback_data = f"confirm_globan_{key}"
                    )
                ]
            ])
            
            # Отправляем сообщение с кнопками под пересланным
            await message.bot.send_message(
                chat_id=user,
                text=f"https://t.me/c/{str(message.chat.id)[4:]}/{str(message.message_thread_id) + '/' if message.message_thread_id != None else ''}{message.message_id}\n📝 Действия с сообщением:",
                reply_markup=keyboard
            )
            
            logger.info(f"📤 Переслано сообщение с кнопками: {text[:50]}...")
    except KeyError as e:
        await message.bot.send_message(message.from_user.id,"❌На чат "+f"<a href='https://t.me/{message.chat.username}'>{message.chat.full_name}</a>"+ " не назначен ни один админ.")
    except Exception as e:
        logger.error(f"❌ Ошибка пересылки: {e}")

@router.callback_query(lambda c: c.data.startswith('action_'))
async def handle_action(callback: types.CallbackQuery):
    """Обработка нажатий кнопок"""
    with get_sesion() as session:
        _, action, msg_id_str = callback.data.split('_')
        msg_id = int(msg_id_str)

        statement = select(CheckedText).where(CheckedText.id == msg_id)
        msg = session.scalars(statement).first()
        
        # Получаем сохраненный текст
        if msg.message_id not in pending_messages:
            await callback.answer("❌ Сообщение уже обработано", show_alert=True)
            await callback.message.delete()
            return





        if action == 'skip':
            msg.approwed_is_spam = False
            msg.ts_of_approve = datetime.now()
            msg.is_checked = True
            session.commit()
            await callback.message.delete()
            await callback.answer("Пропущено ✅")
            return
    
    
        
        
def stable():
    return "ok"