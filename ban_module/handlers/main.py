from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import config
import logging
from ban_module.ban_time import parse_rs
from ban_module.punishments import add_mute, un_mute
from sqlalchemy.ext.asyncio import AsyncSession
logger = logging.getLogger(__name__)
router = Router()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class AdminAction(CallbackData, prefix="adm"):
    action: str  # "mute" или "ban"
    user_id: int # ID нарушителя

# Фабрика для кнопок выбора времени
class TimeChoice(CallbackData, prefix="time"):
    duration: int # Время в минутах (например: 15, 60, 1440)

# Состояние FSM
class AdminTarget(StatesGroup):
    choosing_time = State() # Ждем, пока админ выберет или введет время
@router.message(Command("mute"))
async def add_white_example(message: types.Message, db_session: AsyncSession):
    
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    tm  = message.text.replace("/mute", "").strip()
    target_id = message.reply_to_message.from_user.id
    time,reason,duration = parse_rs(tm)
    if await add_mute(db_session,target_id,message.from_user.id,reason,message.chat.id,time) == True:
        await message.answer("Мут выдан\nДлительность: "+duration)

@router.message(Command("unmute"))
async def add_white_example(message: types.Message, db_session: AsyncSession):
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    if await un_mute(db_session,message.reply_to_message.from_user.id,message.chat.id ) == True:
        await message.answer("Пользователь размучен.")
    else:
        await message.answer("Не удалось размутить пользователя, проверьте замучен ли пользователь.")

    
@router.callback_query(lambda c: c.data.startswith('select_punisment'))
async def handle_action(callback: types.CallbackQuery):
    if not callback.data:
      return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="😶Мут",
            callback_data=AdminAction(action="mute",user_id=callback.data.split("_")[2]))],
        [InlineKeyboardButton(text="🚨Глобан", callback_data=AdminAction(action="globan",user_id=callback.data.split("_")[2]),
        InlineKeyboardButton(text="⛔Бан",callback_data=AdminAction(action="ban",user_id=callback.data.split("_")[2]))]
    ])
    if not callback.message:
        return
    callback.message.answer("Выберите наказание для пользователя "+callback.data.split("_")[2], reply_markup=keyboard)

@router.callback_query(AdminAction.filter())
async def process_admin_action(callback: types.CallbackQuery, callback_data: AdminAction, state: FSMContext):
    # Сохраняем тип действия и ID юзера в контекст FSM
    await state.update_data(action=callback_data.action, target_id=callback_data.user_id)
    # Переводим админа в состояние ожидания времени
    await state.set_state(AdminTarget.choosing_time)

    # Строим клавиатуру времени
    builder = InlineKeyboardBuilder()
    builder.button(text="15 мин", callback_data=TimeChoice(duration=15))
    builder.button(text="1 час", callback_data=TimeChoice(duration=60))
    builder.button(text="1 день", callback_data=TimeChoice(duration=1440))
    builder.button(text="Навсегда", callback_data=TimeChoice(duration=0))
    builder.adjust(2) # Кнопки по 2 в ряд

    await callback.message.edit_text(
        text=f"Вы выбрали: {callback_data.action.upper()}.\nВыберите время блокировки или введите его текстом (в минутах):",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

import datetime

# Вариант А: Админ нажал на кнопку времени
@router.callback_query(AdminTarget.choosing_time, TimeChoice.filter())
async def time_callback_handler(callback: types.CallbackQuery, callback_data: TimeChoice, state: FSMContext):
    data = await state.get_data()
    await state.clear() # Сбрасываем состояние
    
    await execute_punishment(
        message=callback.message, 
        action=data['action'], 
        user_id=data['target_id'], 
        minutes=callback_data.duration
    )
    await callback.answer()

# Вариант Б: Админ решил написать время цифрами в чат вручную
@router.message(AdminTarget.choosing_time)
async def time_message_handler(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите время цифрами (минуты) или нажмите кнопку!")
        return

    minutes = int(message.text)
    data = await state.get_data()
    await state.clear() # Сбрасываем состояние

    await execute_punishment(
        message=message, 
        action=data['action'], 
        user_id=data['target_id'], 
        minutes=minutes
    )

# Функция, которая выполняет мут/бан в Telegram
async def execute_punishment(message: types.Message, action: str, user_id: int, minutes: int):
    # Высчитываем временную метку (until_date)
    # Если minutes == 0, для бана это обычно означает "навсегда"
    until_date = datetime.datetime.now() + datetime.timedelta(minutes=minutes) if minutes > 0 else None

    try:
        if action == "mute":
            # Права для мута (запрещаем отправку сообщений)
            permissions = types.ChatPermissions(can_send_messages=False)
            await message.chat.restrict_member(user_id=user_id, permissions=permissions, until_date=until_date)
            time_str = f"на {minutes} мин." if minutes > 0 else "навсегда"
            await message.answer(f"Пользователь {user_id} замучен {time_str}")
            
        elif action == "ban":
            await message.chat.ban_member(user_id=user_id, until_date=until_date)
            time_str = f"на {minutes} мин." if minutes > 0 else "навсегда"
            await message.answer(f"Пользователь {user_id} забанен {time_str}")
            
    except Exception as e:
        await message.answer(f"Не удалось выполнить действие. @bavav0 Ошибка: {e}")
