from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, User
from ...app.config import config
import logging
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest
logger = logging.getLogger(__name__)
router = Router()
from aiogram.enums import ParseMode
from aiogram import Bot, Router, F
from aiogram.types import ChatPermissions, ChatMemberUpdated, InlineKeyboardButton, CallbackQuery, User
from aiogram.filters import IS_NOT_MEMBER, IS_MEMBER, ChatMemberUpdatedFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ...storage import add_globan_data, endget_globan_data,get_globan_data
router = Router()
rights_cache = {}
from aiogram.types import ChatPermissions, ChatMember
from ads_worker.app.admin_module.handlers.comands import rout,F
def get_permissions_from_member(member: ChatMember) -> ChatPermissions | None:
    """
    Извлекает права пользователя из объекта ChatMember.
    Для restricted - собирает из полей.
    Для administrator - пробует member.permissions, если нет - собирает вручную.
    Для member - возвращает None, так как права равны дефолтным чата (их нужно брать из chat.permissions).
    Для creator, left, banned - возвращает None (ограничивать нельзя).
    """
    if member.status == "restricted":
        # ChatMemberRestricted - все поля есть
        return ChatPermissions(
            can_send_messages=member.can_send_messages,
            can_send_audios=member.can_send_audios,
            can_send_documents=member.can_send_documents,
            can_send_photos=member.can_send_photos,
            can_send_videos=member.can_send_videos,
            can_send_video_notes=member.can_send_video_notes,
            can_send_voice_notes=member.can_send_voice_notes,
            can_send_polls=member.can_send_polls,
            can_send_other_messages=member.can_send_other_messages,
            can_add_web_page_previews=member.can_add_web_page_previews,
            can_change_info=member.can_change_info,
            can_invite_users=member.can_invite_users,
            can_pin_messages=member.can_pin_messages,
            can_manage_topics=member.can_manage_topics
        )
    elif member.status == "administrator":
        # У администратора может быть свойство permissions (в новых версиях)
        if hasattr(member, 'permissions'):
            return member.permissions
        # Иначе собираем вручную (поля должны быть)
        return ChatPermissions(
            can_send_messages=member.can_send_messages,
            can_send_audios=member.can_send_audios,
            can_send_documents=member.can_send_documents,
            can_send_photos=member.can_send_photos,
            can_send_videos=member.can_send_videos,
            can_send_video_notes=member.can_send_video_notes,
            can_send_voice_notes=member.can_send_voice_notes,
            can_send_polls=member.can_send_polls,
            can_send_other_messages=member.can_send_other_messages,
            can_add_web_page_previews=member.can_add_web_page_previews,
            can_change_info=member.can_change_info,
            can_invite_users=member.can_invite_users,
            can_pin_messages=member.can_pin_messages,
            can_manage_topics=member.can_manage_topics
        )
    else:
        # Для member, creator, left, banned — возвращаем None
        return None

async def send_captcha(bot: Bot, chat_id: int, user: User):
    member = await bot.get_chat_member(chat_id, user.id)

    # Пропускаем владельца и администраторов (их нельзя ограничивать)
    if member.status in ("creator", "administrator"):
        return

    # Получаем права чата по умолчанию (пригодятся для обычного участника)
    chat = await bot.get_chat(chat_id)
    default_perms = chat.permissions

    # Определяем, какие права были у пользователя до ограничения
    old_perms = get_permissions_from_member(member)
    if old_perms is None:
        # Для обычного участника (status == "member") используем дефолтные права
        old_perms = default_perms

    # Сохраняем права (в кеше или БД)
    rights_cache[(chat_id, user.id)] = old_perms

    # Ограничиваем: только запрет отправки сообщений
    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=False)
    )

    # Создаём кнопку-каптчу
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Я не робот",
        callback_data=f"captcha_{user.id}"
    ))

    await bot.send_message(
        chat_id=chat_id,
        text=f"Привет, {user.mention_html()}! Пройдите каптчу, чтобы начать общение.",
        reply_markup=builder.as_markup(),
        receiver_user_id=user.id,
        parse_mode=ParseMode.HTML
    )


@rout.event("chat_member")
async def on_user_join(event: ChatMemberUpdated):
    
    old = event.old_chat_member
    new = event.new_chat_member
    if old.status in ("left", "kicked") and new.status == "member":
        
    
        user = event.new_chat_member.user
        await send_captcha(event.bot, event.chat.id, user)
    

@rout.event("callback_query",F.data.startswith("captcha_"))
async def captcha_callback(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    chat_id = callback.message.chat.id

    if callback.from_user.id != user_id:
        await callback.answer("Это не ваша каптча!", show_alert=True)
        return

    old_perms = rights_cache.pop((chat_id, user_id), None)
    if old_perms is None:
        # Если не нашли - используем дефолтные права чата (безопасный fallback)
        chat = await callback.bot.get_chat(chat_id)
        old_perms = chat.permissions

    await callback.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=old_perms
    )

    await callback.answer("✅ Проверка пройдена!")
    
    


@rout.event("callback_query",F.data.startswith('confirm_globan_'))
async def handle_0(callback: types.CallbackQuery):
    parts = callback.data.split('_')
    if len(parts) < 2:
        return
    key = parts[2]
    data = get_globan_data(key)  # уже проверяет день
    if not data:
        await callback.answer("❌ Данные устарели или не найдены", show_alert=True)
        return
    user_id, msg_id, chat_id = data
    # Далее создаём кнопку "Подтвердить", но теперь передаём только ключ
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"globan_{key}"
        )
    ]])
    await callback.message.answer(
        f"Вы точно хотите выдать глобан пользователю {user_id}?",
        reply_markup=keyboard
    )
    await callback.answer()


@rout.event("callback_query",F.data.startswith('globan_'))
async def handle_1(callback: types.CallbackQuery):
    from ...main import bot
    parts = callback.data.split('_')
    if len(parts) < 2:
        await callback.answer("Ошибка данных")
        return
    key = parts[1]
    data = endget_globan_data(key)
    if not data:
        await callback.answer("❌ Данные устарели", show_alert=True)
        return
    user_id, msg_id, chat_id = data

    # Удаляем пересланное сообщение
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
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
    
def stable():
    return "ok"