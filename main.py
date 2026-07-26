import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import config
from app.handlers import admin_router, message_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Инициализация бота
    bot = Bot(token=config.BOT_TOKEN)#, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(admin_router)
    dp.include_router(message_router)
    
    logger.info("🚀 Бот запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
async def add_module(mdl):
    dp.sub_routers.insert(0,mdl)
if __name__ == "__main__":
    asyncio.run(main())