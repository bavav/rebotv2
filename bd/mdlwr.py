
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, ChatPermissions
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import insert,select
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
    """Middleware, который обновляет пользователей и добавляет user_data в data"""
      
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
            # Обновляем текущего пользователя и получаем его объект
            user_obj = await upsert_user_and_increment_messages(
                session=session,
                user_id=event.from_user.id,
                chat_id=event.chat.id,
                rp=False
            )
            # Кладём информацию о пользователе в data
            data["user_data"] = {
                "message_count": user_obj.message_count,
                "user_id": user_obj.id
            }
            
            # Обновляем пользователя, на чьё сообщение ответили (если есть)
            if event.reply_to_message and event.reply_to_message.from_user:
                reply_user = event.reply_to_message.from_user
                await upsert_user_and_increment_messages(
                    session=session,
                    user_id=reply_user.id,
                    chat_id=event.chat.id,
                    rp=True
                )
                # Можно добавить reply_user_data, но нам не нужно
            
            await session.commit()
            
        # Не передаём сессию в хэндлеры!
        return await handler(event, data)


async def upsert_user_and_increment_messages(
    session: AsyncSession, 
    user_id: int, 
    chat_id: int,
    rp: bool
) -> User:   # теперь возвращаем User
    """
    Добавляет пользователя или обновляет его данные,
    а также увеличивает счетчик сообщений на +1 (если не rp).
    Возвращает объект User.
    """
    

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Обновляем существующего
        
        if not rp:
            user.message_count = user.message_count + 1
            user.last_message_at = datetime.now()
            
            
        return user
    else:
        # Создаём нового
        new_user = User(
            id=user_id,
            message_count=0 if rp else 1,  # если это ответ, то счётчик пока 0
            last_message_at=datetime.now(),
            first_message_at=datetime.now()
        )
        session.add(new_user)
        return new_user