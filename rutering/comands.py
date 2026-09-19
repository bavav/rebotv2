from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from ..admin_module.handlers.comands import *

async def test(s):
    await s.answer("gogogogo")
async def c_test(s):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"test"
        )
    ]])
    await s.answer(
        f"Вы точно хотите выдать глобан пользователю 0?",
        reply_markup=keyboard
    )
comands = {
    "add_admin":add_admin,
    "rm_admin":rm_admin,
    "add_chat":add_chat,
    "rm_chat":rm_chat,
    "test":c_test
    
}
callbacks = {
    "test": test
}
async def hndl(message: Message):
    if message.text:
        for i,j in comands.items():
            if message.text.startswith("/"+i):
                await j(message)
                return True
    return False

async def hndl_callback(callback: CallbackQuery):
    if callback.data:
        for i,j in callbacks.items():
            if callback.data.startswith(i):
                await j(callback)
                return True
    return False