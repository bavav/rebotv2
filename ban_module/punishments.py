from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload  # Add this import
from bd.models.main import User, ReputationHistory
from app.config import config
from aiogram.types import ChatPermissions, ChatMemberRestricted, ChatMemberAdministrator
from bd.models.main import Punishment
from typing import Optional

import logging

logger = logging.getLogger(__name__)
async def un_mute(
    session: AsyncSession,
    target_id:int,
    chat_id: int
) -> bool:
    from main import bot
    stmt = (
        select(Punishment)
        .where(Punishment.target_id == target_id)
        .where(Punishment.type == "mute")
        .where(Punishment.is_active == True)
        .order_by(Punishment.created_at.desc())
    )


    
    res = await session.execute(stmt)
    res = res.scalars().all()
    if len(res) == 0:
        return False
    res = res[0]
    restored_permissions = ChatPermissions(**res.previous_permissions)
    logger.debug("Разрешения: "+str(res.previous_permissions))
    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=target_id,
        permissions=restored_permissions
    )
    stmt = (
        select(Punishment)
        .where(Punishment.target_id == target_id)
        .where(Punishment.chat_id == chat_id)
        .where(Punishment.type == "mute")
        .where(Punishment.is_active == True)
        
    )



    res = await session.execute(stmt)
    active_pun = res.scalars().all()

    for i in active_pun:
        i.is_active = False
    await session.commit()
    return True

async def add_mute(
    session: AsyncSession, 
    target_id: int, 
    admin_id: int, 
    reason: str,
    chat_id: int,
    time: int
) -> bool:
    from main import bot
    
    try:
        duration = timedelta(seconds=time)
        expire_date = datetime.now() + duration

        logger.debug("Now: "+ str(datetime.now()))
        logger.debug("Punishment end: "+ str(expire_date))

        # Формируем жесткие ограничения (запрещаем всё)
        limited_permissions = ChatPermissions(
            can_send_messages = False, 
            can_send_audios = False, 
            can_send_documents = False, 
            can_send_photos = False, 
            can_send_videos = False, 
            can_send_video_notes = False, 
            can_send_voice_notes = False, 
            can_send_polls = False, 
            can_send_other_messages = False, 
            can_add_web_page_previews = False, 
            can_change_info = False, 
            can_invite_users = False, 
            can_pin_messages = False, 
            can_manage_topics = False
        )
        current_perms = await bot.get_chat_member(chat_id=chat_id, user_id=target_id)

        
        saved_permissions = {
            "can_send_messages": True, 
            "can_send_audios": True, 
            "can_send_documents": True, 
            "can_send_photos": True, 
            "can_send_videos": True, 
            "can_send_video_notes": True, 
            "can_send_voice_notes": True, 
            "can_send_polls": True, 
            "can_send_other_messages": True, 
            "can_add_web_page_previews": True, 
            "can_change_info": True, 
            "can_invite_users": True, 
            "can_pin_messages": True, 
            "can_manage_topics": True
        }

        
        
        for key in saved_permissions.keys():
            saved_permissions[key] = getattr(current_perms, key, True)

        
        # Отправляем в Telegram. По истечении expire_date мут снимется сам!
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_id,
            permissions=limited_permissions,
            until_date=expire_date
        )
        stmt = (
            select(Punishment)
            .where(Punishment.target_id == target_id)
            .where(Punishment.type == "mute")
            .where(Punishment.is_active == True)
            
        )



        res = await session.execute(stmt)
        active_pun = res.scalars().all()

        for i in active_pun:
            i.is_active = False
        logger.debug("lst perms:"+str(saved_permissions))
        if len(active_pun) > 1:
            saved_permissions = active_pun[0].previous_permissions
            logger.debug("sawed last perms:"+str(saved_permissions))

        new_punishment = Punishment(
            target_id=target_id,
            admin_id=admin_id,
            chat_id=chat_id,
            type="mute",
            reason=reason,
            duration=duration,
            is_active=True,
            previous_permissions=saved_permissions
        )
        session.add(new_punishment)
        await session.commit()
        return True
    except SQLAlchemyError as e:
        await session.rollback()
        logger.debug(f"Database error: {e}")
        return False
    
        
async def get_punishments(
    session: AsyncSession, 
    user_id: int,
    limit: int,
    full: bool,
    type: Optional[str] = None,
    chat_id: Optional[int] = None,
    max_date: Optional[datetime] = None
):
    
    try:
        # Preload the sender relationship to avoid lazy loading issues
        stmt = (
            select(Punishment)
            .where(Punishment.target_id == user_id)
            .where(Punishment.is_active == False)
            .options(selectinload(Punishment.admin))  # Убедитесь, что связь admin есть в Punishment
            .order_by(Punishment.created_at.desc())   # Сортируем по полю из Punishment
            .limit(limit)
        )

        # 2. Условное добавление фильтра по дате
        if max_date:
            stmt = stmt.where(Punishment.created_at >= max_date)
        if chat_id:
            stmt = stmt.where(Punishment.chat_id == chat_id)
        if type:
            stmt = stmt.where(Punishment.type == type)
        res = await session.execute(stmt)
        history_records = res.scalars().all()  # Use scalars() to get proper objects
        logger.debug(history_records)
        n = ""
        for record in history_records:  # Iterate directly over records
            # Access sender safely
            admin_username = record.admin.username if record.admin else "Unknown"
            if full:
                
                n += f"{str(record.created_at)}/{str(record.created_at + record.duration)} - {record.type}({record.duration}) - @{admin_username} - {record.reason}"
            else:
                n += f"{record.type}({record.duration}) - @{admin_username} - {record.reason}"
            n += "\n"
        return n if n else "История наказаний пуста."
    except SQLAlchemyError as e:
        logger.debug(f"Database error: {e}")
        return "Ошибка при получении истории наказаний."
async def get_active_punishments(session: AsyncSession, user_id,chat_id,full:bool):
    try:

        now = datetime.now()
        
        # First, deactivate expired punishments
        stmt = (
            select(Punishment)
            .where(Punishment.target_id == user_id)
            .where(Punishment.chat_id == chat_id)
            .where(Punishment.is_active == True)
        )
        
        res = await session.execute(stmt)
        active_punishments = res.scalars().all()
        
        # Check each punishment individually to handle type conversions properly
        for punishment in active_punishments:
            if punishment.duration is not None and punishment.created_at is not None:
                end_time = punishment.created_at + punishment.duration
                logger.debug(f"Checking punishment {punishment.id}: end={end_time} <= now={now}")
                if end_time <= now:
                    punishment.is_active = False
        
        await session.commit()        
        stmt = (
            select(Punishment)
            .where(Punishment.target_id == user_id)
            .where(Punishment.chat_id == chat_id)
            .where(Punishment.is_active == True)
            .options(selectinload(Punishment.admin))
        )
        res = await session.execute(stmt)
        res = res.scalars().one_or_none()
        n = ""
        if res:
            if full:
                n += f"Активное наказание:\n{res.type} на {res.duration}\nДо {str(res.created_at + res.duration)}\nВыдано: {res.created_at} - @{res.admin.username} - {res.reason}"
            else:
                n += f"Активное наказание:\n{res.type} на {res.duration} - {res.reason}"
        else:
            stmt = (
                select(Punishment)
                .where(Punishment.target_id == user_id)
                .where(Punishment.is_active == True)
                .options(selectinload(Punishment.admin)) 

            )
            res = await session.execute(stmt)
            res = res.scalars().one_or_none()
            if res:
                n += f"У пользователя имееться активное наказание в другом чате, обратитесь к @{res.admin.username}"
            else:
                n += f"У пользователя не имееться активных наказаний"
        return n
    except SQLAlchemyError as e:
        logger.debug(f"Database error: {e}")
        return "Ошибка при получении истории наказаний."

