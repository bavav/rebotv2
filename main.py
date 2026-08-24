import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import config
from app.handlers import admin_router, message_router
from admin_module.handlers.comands import router as admin_module_router
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from ban_module.handlers.main import router as ban_router
from bd.models.main import Base
from bd.mdlwr import DbSessionMiddleware ,DbUserUpdaterMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
bot = Bot(token=config.BOT_TOKEN)#, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
async def main():
    # Инициализация бота
    engine = create_async_engine("sqlite+aiosqlite:///database.db")
    
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Регистрация роутеров
    dp.include_router(admin_router)
    message_router.message.outer_middleware(DbUserUpdaterMiddleware(session_maker))
    
    dp.include_router(message_router)

    dp.include_router(admin_module_router)
    
    ban_router.message.middleware(DbSessionMiddleware(session_maker=session_maker))
    dp.include_router(ban_router)
    logger.info("🚀 Бот запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

    
if __name__ == "__main__":
    asyncio.run(main())
