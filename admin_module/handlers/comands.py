from aiogram import Router, types
from aiogram.filters import Command


from app.config import config,get_admins,add_aid,rm_aid,add_chid,rm_chid
import logging


logger = logging.getLogger("admin_module"+ __name__)
router = Router()


@router.message(Command("add_admin"))
async def set_ml_threshold(message: types.Message):
    if message.from_user.id not in get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    text = message.text.replace("/add_admin", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /add_admin [userid] [chat_id]"
            )
            return
    
    r = add_aid(int(text.split()[0]),int(text.split()[1]))
    if r == True:
        await message.answer("Добавлены админ с id: "+text.split()[0]+" в чат "+text.split()[1])
    else:
        await message.answer("Админ с id: "+text.split()[0]+" уже управляет чатом "+text.split()[1])

@router.message(Command("get_admins"))
async def getadmins(message: types.Message):
    if message.from_user.id not in get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    lines = []
    for key, values in config.ADMIN_IDS.items():
        lines.append(f'{key}:')
        for item in values:
            lines.append(f" - {item}")
    result ="\n".join(lines)
    await message.answer(result)
    

@router.message(Command("rm_admin"))
async def rmadmin(message: types.Message):
    if message.from_user.id not in get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    text = message.text.replace("/rm_admin", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /rm_admin [userid] [chat_id]"
            )
            return
    
    r = rm_aid(int(text.split()[0]),int(text.split()[1]))
    if r == True:
        await message.answer("Убран админ с id: "+text.split()[0]+" из чата "+text.split()[1])
    else:
        await message.answer("Пользователь с id: "+text.split()[0]+" не являеться админом чата "+text.split()[1])
        
@router.message(Command("add_chat"))
async def addstk(message: types.Message):
    # Проверка прав (оставляем как есть)
    if message.from_user.id not in get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return

    # Парсим аргументы
    text = message.text.replace("/add_chat", "").strip()
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply("ℹ️ Используйте: /add_chat [chat_id]")
            return

    try:
        chat_id = int(text.split()[0])
    except ValueError:
        await message.reply("❌ Неверный ID чата. Должно быть число.")
        return

    # Проверяем, является ли бот администратором в этом чате
    try:
        bot_member = await message.bot.get_chat_member(chat_id, message.bot.id)
    except Exception as e:
        # Если бот не может получить информацию (например, чат не существует или бот не участник)
        await message.reply(f"❌ Не удалось проверить права бота в чате {chat_id}. Ошибка: {e}")
        return

    # Статусы, при которых бот считается администратором
    if bot_member.status not in ('administrator', 'creator'):
        await message.reply(
            f"❌ Бот не является администратором в чате {chat_id}.\n"
            "Добавьте бота в чат как администратора и повторите команду."
        )
        return

    # Дополнительно можно проверить наличие критически важных прав
    required_perms = {
        'can_delete_messages': 'удалять сообщения',
        'can_restrict_members': 'ограничивать участников',
        'can_ban_users': 'банить участников'
    }
    missing = []
    if bot_member.status == 'administrator':
        for perm, name in required_perms.items():
            if not getattr(bot_member, perm, False):
                missing.append(name)
    if missing:
        await message.reply(
            f"⚠️ Бот в чате {chat_id} не имеет прав: {', '.join(missing)}.\n"
            "Рекомендуется дать эти права для корректной работы."
        )
        # Можно либо прервать добавление, либо только предупредить.
        # Здесь мы только предупреждаем, но продолжаем добавление.
        # Если хотите запретить — раскомментируйте return.

    # Добавляем чат в сетку
    r = add_chid(chat_id)
    if r:
        await message.answer(f"✅ Чат с id {chat_id} добавлен в сетку")
    else:
        await message.answer(f"ℹ️ Чат с id {chat_id} уже в сетке")
        
@router.message(Command("rm_chat"))
async def rmstk(message: types.Message):
    if message.from_user.id not in get_admins() and message.from_user.id != config.DEV_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    text = message.text.replace("/rm_chat", "").strip()
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /rm_chat [chat_id]"
            )
            return
    r = rm_chid(int(text.split()[0]))
    if r:
        await message.answer("Чат с id" +text.split()[0] + " убран из сетки" )
    else:
        await message.answer("Чат с id" +text.split()[0] + " не в сетке" )