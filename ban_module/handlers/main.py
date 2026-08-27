from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, User
from app.config import config
import logging
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest
logger = logging.getLogger(__name__)
router = Router()
async def send_captcha(bot: Bot, chat_id: int, user: User):
    # 1. Сразу ограничиваем пользователя (запрещаем писать)
    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=False)
    )

    # 2. Создаём клавиатуру с проверкой
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Я не робот",
        callback_data=f"captcha_{user.id}"
    ))

    # 3. Отправляем эфемерное сообщение (видит только пользователь)
    await bot.send_message(
        chat_id=chat_id,
        text=f"Привет, {user.mention_html()}! Пройдите каптчу, чтобы начать общение.",
        reply_markup=builder.as_markup(),
        receiver_user_id=user.id   # <-- эфемерность
    )
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER)
)
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    user = event.new_chat_member.user
    await send_captcha(bot, event.chat.id, user)
@router.callback_query(F.data.startswith("captcha_"))
async def captcha_callback(callback: CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])

    # Проверяем, что нажал тот же пользователь
    if callback.from_user.id != user_id:
        await callback.answer("Это не ваша каптча!", show_alert=True)
        return

    # Если каптча пройдена
    await callback.answer("✅ Проверка пройдена!")

    # Снимаем ограничения (если они были наложены)
    await bot.restrict_chat_member(
        chat_id=callback.message.chat.id,
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=True) # Пример полных прав
    )

    # Удаляем эфемерное сообщение (оно всё равно видно только пользователю)
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    
    
@router.callback_query(lambda c: c.data.startswith('confirm_globan'))
async def handle_0(callback: types.CallbackQuery):
    parts = callback.data.split('_')
    if len(parts) < 3:
        return
    msg_id = int(parts[1])      # ID пересланного сообщения
    user_id = int(parts[2])     # ID пользователя, которого баним

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"globan_{user_id}_{msg_id}"   # передаём оба ID
        )
    ]])
    await callback.message.answer(
        f"Вы точно хотите выдать глобан пользователю {user_id}?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith('globan'))
async def handle_1(callback: types.CallbackQuery):
    from main import bot

    parts = callback.data.split('_')
    if len(parts) < 3:
        await callback.answer("Ошибка данных")
        return

    user_id = int(parts[1])
    msg_id = int(parts[2])   # ID пересланного сообщения

    # Удаляем пересланное сообщение
    try:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
    except Exception as e:
        logger.error(f"Не удалось удалить пересланное сообщение: {e}")

    # Удаляем сообщение с кнопкой подтверждения
    try:
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение подтверждения: {e}")

    # Выполняем бан во всех чатах
    for chat_id in config.CHATS_IDS:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        except TelegramBadRequest:
            continue

    await callback.answer("✅ Пользователь забанен, сообщение удалено")