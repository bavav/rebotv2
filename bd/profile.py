from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload  # Add this import
from bd.models.main import User, ReputationHistory
import logging

logger = logging.getLogger(__name__)

async def get_user_messages_count(session: AsyncSession, id: int):
    try:
        stmt = (
            select(User)
            .where(User.id == id)
        )
        res = await session.execute(stmt)
        res = res.scalar_one_or_none()
        if res:
            return res.message_count
        return None
    except SQLAlchemyError as e:
        logger.debug(f"Database error: {e}")
        return None
async def get_last_message_time(session: AsyncSession, id: int):
    try:
        stmt = (
            select(User)
            .where(User.id == id)
        )
        res = await session.execute(stmt)
        res = res.scalar_one_or_none()
        if res:
            return  res.last_message_at
        return None
    except SQLAlchemyError as e:
        logger.debug(f"Database error: {e}")
        return None
