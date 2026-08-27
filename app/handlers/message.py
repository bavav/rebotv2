# message.py - альтернативный вариант с кнопками на пересланном сообщении
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import config
from app.filters.rag_filter import RagFilter
from app.services.rag_service import ragservice
import logging

logger = logging.getLogger(__name__)
router = Router()

# Словарь для хранения текстов сообщений
pending_messages = {}

@router.message(RagFilter())
async def forward_filtered_message(message: types.Message):
    """Пересылает сообщение с кнопками для добавления в белый/черный список"""
    logger.debug("f: "+str(config.ADMIN_IDS.keys())+" "+str(message.chat.id))
    try:
        # Получаем текст сообщения
        text = message.text or message.caption or ""
        
        # Сохраняем текст для последующего использования
        pending_messages[message.message_id] = text
        
        # Пересылаем целевому пользователю
        
        for user in config.ADMIN_IDS[message.chat.id]:
            forwarded = await message.forward(chat_id=user)
            
            # Создаем кнопки для действий
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ В белый", 
                        callback_data=f"action_white_{message.message_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ В черный", 
                        callback_data=f"action_black_{message.message_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⏭ Пропустить", 
                        callback_data=f"action_skip_{message.message_id}"
                    ),
                    InlineKeyboardButton(
                        text="🚫 Глобан", 
                        callback_data=f"confirm_globan_{message.message_id}_{message.from_user.id}"
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
        
    except Exception as e:
        logger.error(f"❌ Ошибка пересылки: {e}")

@router.callback_query(lambda c: c.data.startswith('action_'))
async def handle_action(callback: types.CallbackQuery):
    """Обработка нажатий кнопок"""
    _, action, msg_id_str = callback.data.split('_')
    msg_id = int(msg_id_str)
    
    # Получаем сохраненный текст
    if msg_id not in pending_messages:
        await callback.answer("❌ Сообщение уже обработано", show_alert=True)
        await callback.message.delete()
        return
    
    text = pending_messages.pop(msg_id)
    
    # Инициализируем RAG сервис
    rag_service = rag_service
    
    if action == 'skip':
        await callback.message.delete()
        await callback.answer("Пропущено ✅")
        return
    
    elif action == 'white':
        # Добавляем в белый список
        doc_id = rag_service.add_white_example(text)
        stats = rag_service.get_statistics()
        
        await callback.message.edit_text(
            f"✅ Добавлено в БЕЛЫЙ список!\n"
            
            f"📝 ID: {doc_id[:8]}...\n" if callback.from_user.id == config.DEV_ID else ""
            f"📊 Всего примеров: {stats}" if callback.from_user.id == config.DEV_ID else ""
        )
        await callback.answer("Добавлено в белый список ✅")
        logger.info(f"➕ Добавлено в белый список: {text[:50]}...")
        
    elif action == 'black':
        # Добавляем в черный список
        doc_id = rag_service.add_black_example(text)
        stats = rag_service.get_statistics()
        
        await callback.message.edit_text(
            f"❌ Добавлено в ЧЕРНЫЙ список!\n"
            f"📝 ID: {doc_id[:8]}...\n" if callback.from_user.id == config.DEV_ID else ""
            f"📊 Всего примеров: {stats}" if callback.from_user.id == config.DEV_ID else ""
        )
        await callback.answer("Добавлено в черный список ❌")
        logger.info(f"➕ Добавлено в черный список: {text[:50]}...")