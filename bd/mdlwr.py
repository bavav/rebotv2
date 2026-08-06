
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, ChatPermissions
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import insert
from sqlalchemy import update as sa_update
from bd.models.main import User
from datetime import datetime, timedelta


class DbSessionMiddleware(BaseMiddleware):
    """Middleware, который предоставляет сессию БД, но НЕ обновляет пользователей"""
    
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)

        async with self.session_maker() as session:
            data["db_session"] = session
            return await handler(event, data)


class DbUserUpdaterMiddleware(BaseMiddleware):
    """Middleware, который обновляет пользователей, но НЕ предоставляет сессию"""
      
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)

        async with self.session_maker() as session:
            # Обновляем текущего пользователя
            await upsert_user_and_increment_messages(
                session=session,
                user_id=event.from_user.id,
                chat_id=event.chat.id,
                username=event.from_user.username,
                full_name=event.from_user.full_name,
                rp= False
                
            )
            
            # Обновляем пользователя, на чьё сообщение ответили (если есть)
            if event.reply_to_message and event.reply_to_message.from_user:
                reply_user = event.reply_to_message.from_user
                await upsert_user_and_increment_messages(
                    session=session,
                    user_id=reply_user.id,
                    chat_id=event.chat.id,
                    username=reply_user.username,
                    full_name=reply_user.full_name,
                    rp = True
                )
            
            await session.commit()
            
        # Не передаём сессию в хэндлеры!
        return await handler(event, data)


async def upsert_user_and_increment_messages(
    session: AsyncSession, 
    user_id: int, 
    chat_id: int,
    username: str | None, 
    full_name: str,
    rp: bool
) -> None:
    """
    Добавляет пользователя или обновляет его данные,
    а также увеличивает счетчик сообщений на +1.
    Для SQLite используется ON CONFLICT DO UPDATE
    """
    # В SQLite нет поддержки ON CONFLICT, используем подход с INSERT OR REPLACE
    # или проверку существования записи
    from main import bot 
    # Проверяем, существует ли пользователь
    from sqlalchemy import select
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Обновляем существующего пользователя
        user.username = username
        user.full_name = full_name
        if rp != True:
            user.message_count = user.message_count + 1
            user.last_message_at = datetime.now()
            if user.message_count > 1 and (user.first_message_at + timedelta(minutes=5)) <= datetime.now():
                user.can_send_photos = True
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

                current_perms = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)


        
                for key in saved_permissions.keys():
                    saved_permissions[key] = getattr(current_perms, key, True)
                saved_permissions["can_send_photos"] = True
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(**saved_permissions)
                )

                

    else:
        # Создаём нового пользователя
        new_user = User(
            id=user_id,
            username=username,
            full_name=full_name,
            message_count=0,
            last_message_at = datetime.now(),
            first_message_at = datetime.now()
        )
        session.add(new_user)
    
    # Коммит будет выполнен в middleware
