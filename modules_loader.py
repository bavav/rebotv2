from aiogram import Bot,Dispatcher,Router,F
from aiogram.types import Message
from aiogram.filters import Command,Filter

from app.config import config

import logging

logger = logging.getLogger(__name__)
router = Router()
class IsModuleActive(Filter):
    def __init__(self,r_name: str):
        self.r_name= r_name

    async def __call__(self,message: Message):
        return self.r_name in active_modules

from admin_module.handlers.comands import router as admin_router
plugins = [
    "admin",

]
active_modules = [

]





@router.message(Command("add_module"))
async def add_white_example(message: Message):
    from main import dp
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    if not message.text:
        return
    text = message.text.replace("/add_module", "").strip()
    if not text:
        await message.reply(
            "ℹ️ Используйте: /add_module [имя модуля]"
        )
        return
    if not text in plugins:
        await message.answer("Модуль не найден")
        await message.answer("Список модулей:\n"+"\n".join(plugins))
        return
    if text not in active_modules:
        active_modules.append(text)
        
        await message.answer("Модуль загружен")
@router.message(Command("rm_module"))
async def add_white_example(message: Message):
    from main import dp
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    if not message.text:
        return
    text = message.text.replace("/add_module", "").strip()
    if not text:
        await message.reply(
            "ℹ️ Используйте: /rm_module [имя модуля]"
        )
        return
    if not text in active_modules:
        await message.answer("Модуль не найден в списке загруженых модулей")
        await message.answer("Список загруженых модулей:\n"+"\n".join(active_modules))
    if text in active_modules:
        
        active_modules.pop(text)
        await message.answer("Модуль выгружен")
@router.message(Command("list_modules"))
async def add_white_example(message: Message):
    from main import dp
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    await message.answer("Список загруженых модулей:\n"+"\n".join(active_modules))
    await message.answer("Список не загруженых модулей:\n"+"\n".join(([i for i in plugins if i not in set(active_modules)])))