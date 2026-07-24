import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import config
from app.handlers import admin_commands


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from aiogram import Router, types
from aiogram.filters import Command
from app.filters.rag_filter import RagFilter

router = Router()
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
@router.message(RagFilter())  # <-- Вот здесь применяется наш кастомный фильтр
async def forward_filtered_message(message: types.Message):
    # Фильтр сработал (сообщение рекламное) -> пересылаем
    target_user_id = config.TARGET_USER_ID
    await message.forward(chat_id=target_user_id)
    print(message.message_thread_id)
    await bot.send_message(target_user_id,f"https://t.me/c/{str(message.chat.id)[4:]}/{str(message.message_thread_id) + '/' if message.message_thread_id != None else ''}{message.message_id}")
async def main():
    # Инициализация бота
    
    
    
    # Регистрация роутеров
    dp.include_router(admin_commands.router)
    dp.include_router(router)
    
    # Запуск
    logger.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())