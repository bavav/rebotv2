from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import config
import logging
from ban_module.ban_time import parse_rs
from ban_module.punishments import add_mute, un_mute
from sqlalchemy.ext.asyncio import AsyncSession
logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("mute"))
async def add_white_example(message: types.Message, db_session: AsyncSession):
    
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    tm  = message.text.replace("/mute", "").strip()
    target_id = message.reply_to_message.from_user.id
    time,reason,duration = parse_rs(tm)
    if await add_mute(db_session,target_id,message.from_user.id,reason,message.chat.id,time) == True:
        await message.answer("Мут выдан\nДлительность: "+duration)

@router.message(Command("unmute"))
async def add_white_example(message: types.Message, db_session: AsyncSession):
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    if await un_mute(db_session,message.reply_to_message.from_user.id,message.chat.id ) == True:
        await message.answer("Пользователь размучен.")
    else:
        await message.answer("Не удалось размутить пользователя, проверьте замучен ли пользователь.")

    
