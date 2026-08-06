from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload  # Add this import
from bd.models.main import User, ReputationHistory
import logging

logger = logging.getLogger(__name__)

async def change_user_reputation(
    session: AsyncSession, 
    target_id: int, 
    sender_id: int, 
    change_value: int,
    cooldown_minutes: int = 5
) -> tuple[bool, str]:
    if target_id == sender_id:
        return False, "Нельзя изменять репутацию самому себе!"

    try:
        # Используем UTC время для проверки
        now_utc = datetime.now(timezone.utc)
        cooldown_time = now_utc - timedelta(minutes=cooldown_minutes)
        
        
        
        cooldown_stmt = (
            select(ReputationHistory)
            .where(
                ReputationHistory.sender_id == sender_id,
                ReputationHistory.created_at >= cooldown_time
            )
            .order_by(ReputationHistory.created_at.desc())
            .limit(1)
        )

        cooldown_check = await session.execute(cooldown_stmt)
        last_record = cooldown_check.scalar_one_or_none()
        
        if last_record:
            
            return False, f"Изменять репутацию можно не чаще, чем раз в {cooldown_minutes} минут!"

        # Обновляем репутацию
        update_stmt = (
            update(User)
            .where(User.id == target_id)
            .values(reputation=User.reputation + change_value)
        )
        result = await session.execute(update_stmt)
        
        if result.rowcount == 0:
            return False, "Пользователь не найден в базе данных бота."

        # Создаем запись с UTC временем
        history_entry = ReputationHistory(
            target_id=target_id,
            sender_id=sender_id,
            change=change_value,
            created_at=now_utc
        )
        session.add(history_entry)

        await session.commit()
        return True, "Репутация успешно изменена!"

    except SQLAlchemyError as e:
        await session.rollback()
        logger.debug(f"Database error: {e}")
        return False, "Ошибка базы данных при изменении репутации."

async def get_rep(session: AsyncSession, id: int):
    try:
        stmt = (
            select(User)
            .where(User.id == id)
        )
        res = await session.execute(stmt)
        res = res.scalar_one_or_none()
        if res:
            return res.reputation
        return None
    except SQLAlchemyError as e:
        logger.debug(f"Database error: {e}")
        return None

async def get_rep_history(session: AsyncSession, id: int):
    try:
        # Preload the sender relationship to avoid lazy loading issues
        stmt = (
            select(ReputationHistory)
            .where(ReputationHistory.target_id == id)
            .options(selectinload(ReputationHistory.sender))  # Explicitly load the relationship
            .order_by(ReputationHistory.created_at.desc())
            .limit(10)
        )
        res = await session.execute(stmt)
        history_records = res.scalars().all()  # Use scalars() to get proper objects
        
        n = ""
        for record in history_records:  # Iterate directly over records
            # Access sender safely
            sender_username = record.sender.username if record.sender else "Unknown"
            n += f"{record.created_at} - ({'+' if record.change > 0 else ''}{record.change}) - @{sender_username}"
            n += "\n"
        return n if n else "История репутации пуста."
    except SQLAlchemyError as e:
        logger.debug(f"Database error: {e}")
        return "Ошибка при получении истории репутации."