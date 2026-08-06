from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import Command
from bd.rep import change_user_reputation,get_rep,get_rep_history
from ban_module.punishments import get_punishments, get_active_punishments
from bd.profile import get_last_message_time,get_user_messages_count
router = Router()

@router.message(F.text == "+")
async def plus_rep_handler(message: Message, db_session: AsyncSession):
    # Проверяем, что это ответ на другое сообщение
    if not message.reply_to_message:
        return await message.reply("Вы должны ответить на сообщение пользователя!")

    target_id = message.reply_to_message.from_user.id
    sender_id = message.from_user.id

    success, msg = await change_user_reputation(
        session=db_session, 
        target_id=target_id, 
        sender_id=sender_id, 
        change_value=1,
        cooldown_minutes=5
    )

    if success:
        await message.answer(msg)
    else:
        await message.answer(msg)
@router.message(F.text == "-")
async def minus_rep_handler(message: Message, db_session: AsyncSession):
    # Проверяем, что это ответ на другое сообщение
    if not message.reply_to_message:
        return await message.reply("Вы должны ответить на сообщение пользователя!")

    target_id = message.reply_to_message.from_user.id
    sender_id = message.from_user.id

    success, msg = await change_user_reputation(
        session=db_session, 
        target_id=target_id, 
        sender_id=sender_id, 
        change_value=-1,
        cooldown_minutes=5
    )

    if success:
        await message.answer(msg)
    else:
        await message.answer(msg)
@router.message(Command("get_rep"))
async def his_rep_handler(message: Message, db_session: AsyncSession):
    # Проверяем, что это ответ на другое сообщение
    if not message.reply_to_message:
        return await message.reply("Вы должны ответить на сообщение пользователя!")

    target_id = message.reply_to_message.from_user.id

    
    n = ""
    n += f"Пользователь @{message.reply_to_message.from_user.username}\n"
    n += "------------\n"
    n += f"Репутация: {str(await get_rep(db_session, message.reply_to_message.from_user.id))} \n"
    n += "------------\n"
    n += "История: \n"
    n += str(await get_rep_history(db_session, message.reply_to_message.from_user.id))
    
    await message.answer(n)

@router.message(Command("profile"))
async def profile_s(message: Message, db_session: AsyncSession):
    if not message.reply_to_message:
        return await message.reply("Вы должны ответить на сообщение пользователя!")

    target_id = message.reply_to_message.from_user.id

    
    n = ""
    n += f"Пользователь @{message.reply_to_message.from_user.username}\n"
    n += "------------\n"
    n += f"Репутация: {str(await get_rep(db_session, message.reply_to_message.from_user.id))} \n"
    n += "------------\n"
    n += "Количество сообщений: \n"
    n += str(await get_user_messages_count(db_session, message.reply_to_message.from_user.id))
    n += "\nПоследнее сообщение: \n"
    n += str(await get_last_message_time(db_session, message.reply_to_message.from_user.id))
    n += "\n------------\n"
    n += str(await get_active_punishments(db_session, message.reply_to_message.from_user.id,message.chat.id,False))
    n += "\n------------\n"
    n += f"Наказания:\n {str(await get_punishments(db_session, message.reply_to_message.from_user.id,5,False))} \n"
    n += "------------\n"
    
    await message.answer(n)

@router.message(Command("fprofile"))
async def profile_f(message: Message, db_session: AsyncSession):
    if not message.reply_to_message:
        return await message.reply("Вы должны ответить на сообщение пользователя!")

    target_id = message.reply_to_message.from_user.id

    
    n = ""
    n += f"Пользователь @{message.reply_to_message.from_user.username}\n"
    n += "------------\n"
    n += f"Репутация: {str(await get_rep(db_session, message.reply_to_message.from_user.id))} \n"
    n += "------------\n"
    n += "Количество сообщений: \n"
    n += str(await get_user_messages_count(db_session, message.reply_to_message.from_user.id))
    n += "\nПоследнее сообщение: \n"
    n += str(await get_last_message_time(db_session, message.reply_to_message.from_user.id))
    n += "\n------------\n"
    n += str(await get_active_punishments(db_session, message.reply_to_message.from_user.id,message.chat.id,True))
    n += "\n------------\n"
    n += f"Наказания:\n {str(await get_punishments(db_session, message.reply_to_message.from_user.id,5,True))} \n"
    n += "------------\n"
    
    await message.answer(n)
