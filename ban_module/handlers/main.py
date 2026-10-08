from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, ChatPermissions, InlineKeyboardMarkup,
    InlineKeyboardButton, User,
)
from ...app.config import config
from ...cache import save_rights, pop_rights   # <-- наш модуль
import logging
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from ...storage import add_globan_data, endget_globan_data, get_globan_data
from aiogram.types import ChatPermissions, ChatMember
from ads_worker.app.admin_module.handlers.comands import rout, F
from ...app.services.ml_errors import CheckedText, get_sesion
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router()


def get_permissions_from_member(member: ChatMember) -> ChatPermissions | None:
    """(без изменений — оставил как было)"""
    if member.status == "restricted":
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
            can_manage_topics=member.can_manage_topics,
        )
    elif member.status == "administrator":
        if hasattr(member, 'permissions'):
            return member.permissions
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
            can_manage_topics=member.can_manage_topics,
        )
    return None


async def send_captcha(bot: Bot, chat_id: int, user: User):
    member = await bot.get_chat_member(chat_id, user.id)

    if member.status in ("creator", "administrator"):
        return

    chat = await bot.get_chat(chat_id)
    default_perms = chat.permissions

    old_perms = get_permissions_from_member(member)
    if old_perms is None:
        old_perms = default_perms

    # ⬇️ было: rights_cache[(chat_id, user.id)] = old_perms
    await save_rights(chat_id, user.id, old_perms)

    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=False),
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Я не робот",
        callback_data=f"captcha_{user.id}",
    ))

    await bot.send_message(
        chat_id=chat_id,
        text=f"Привет, {user.mention_html()}! Пройдите каптчу, чтобы начать общение.",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML,
    )


@rout.event("chat_member")
async def on_user_join(event: ChatMemberUpdated):
    old = event.old_chat_member
    new = event.new_chat_member
    if old.status in ("left", "kicked") and new.status == "member":
        user = event.new_chat_member.user
        await send_captcha(event.bot, event.chat.id, user)


@rout.event("callback_query", F.data.startswith("captcha_"))
async def captcha_callback(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    chat_id = callback.message.chat.id

    if callback.from_user.id != user_id:
        await callback.answer("Это не ваша каптча!", show_alert=True)
        return

    
    old_perms = await pop_rights(chat_id, user_id)

    if old_perms is None:
        chat = await callback.bot.get_chat(chat_id)
        old_perms = chat.permissions

    await callback.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=old_perms,
    )

    await callback.answer("✅ Проверка пройдена!")


@rout.event("callback_query", F.data.startswith('confirm_globan_'))
async def handle_0(callback: types.CallbackQuery):
    with get_sesion() as session:
        parts = callback.data.split('_')
        if len(parts) < 2:
            return
        key = parts[2]
        
        
        statement = select(CheckedText).where(CheckedText.id == key)
        msg = session.scalars(statement).first()
        
        
        if not msg:
            await callback.answer("❌ Данные устарели или не найдены", show_alert=True)
            return
        user_id, msg_id, chat_id = msg.from_user_id,msg.message_id,msg.chat_id
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"globan_{key}",
            )
        ]])
        await callback.message.answer(
            f"Вы точно хотите выдать глобан пользователю {user_id}?",
            reply_markup=keyboard,
        )
        await callback.answer()


@rout.event("callback_query", F.data.startswith('globan_'))
async def handle_1(callback: types.CallbackQuery):
    from ...main import bot
    with get_sesion() as session:
        parts = callback.data.split('_')
        if len(parts) < 2:
            await callback.answer("Ошибка данных")
            return
        key = parts[1]
        
            
        statement = select(CheckedText).where(CheckedText.id == key)
        msg = session.scalars(statement).first()
        msg.approwed_is_spam = True
        msg.is_checked = True
        session.commit()
        if not msg:
            await callback.answer("❌ Данные не найдены", show_alert=True)
            return
        user_id, msg_id, chat_id = msg.from_user_id,msg.message_id,msg.chat_id

        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            logger.error(f"Не удалось удалить пересланное сообщение: {e}")

        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение подтверждения: {e}")

        for chat_id in config.CHATS_IDS:
            try:
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            except TelegramBadRequest:
                continue

        await callback.answer("✅ Пользователь забанен, сообщение удалено")

@rout.event("message", F.text.lower() =='глобан')
async def globan(msg: types.Message):
    from ...main import bot
    
    if not msg.reply_to_message:
        await msg.answer("❌Необходимо ответить на сообщение.",receiver_user_id=msg.from_user.id)
        await msg.delete()
        return
    
    user_id, msg_id, chat_id = msg.reply_to_message.from_user.id, msg.reply_to_message.message_id,msg.chat.id
    
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение: {e}")
    
    try:
        await msg.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение 'Глобан': {e}")
    
    for chat_id in config.CHATS_IDS:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        except TelegramBadRequest:
            continue
    if msg.reply_to_message.text:
        with get_sesion() as session:
            new_text = CheckedText(text=msg.text,from_user_id=msg.from_user.id,message_id=msg.message_id,chat_id = msg.chat.id,is_spam = True,reason="admin_manual_globan",confidence=1.0)
            session.add(new_text)
            session.commit()  
    
    await msg.answer("✅ Пользователь забанен, сообщение удалено",receiver_user_id=msg.from_user.id)
def stable():
    return "ok"