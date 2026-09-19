from aiogram import Router, types
from aiogram.filters import Command
from ....app.app.config import config, get_admins, add_aid, rm_aid, add_chid, rm_chid
import logging

logger = logging.getLogger("admin_module" + __name__)
router = Router()
import shared.app.router as rt
rout = rt.RabbitRouter()
F = rt.MagicFilter()
# ========== Вспомогательные функции ==========
async def resolve_user_id(bot, user_input: str) -> int | None:
    """Получить user_id из числа или username (с @ или без)."""
    user_input = user_input.strip()
    if not user_input:
        return None
    # Попробуем как число
    try:
        return int(user_input)
    except ValueError:
        pass
    # Как username (убираем @ в начале)
    if user_input.startswith("@"):
        user_input = user_input[1:]
    try:
        chat = await bot.get_chat(f"@{user_input}")
        return chat.id
    except Exception:
        return None


async def resolve_chat_id(bot, chat_input: str) -> int | None:
    """Получить chat_id из числа или username (с @ или без)."""
    chat_input = chat_input.strip()
    if not chat_input:
        return None
    try:
        return int(chat_input)
    except ValueError:
        pass
    if chat_input.startswith("@"):
        chat_input = chat_input[1:]
    try:
        chat = await bot.get_chat(f"@{chat_input}")
        return chat.id
    except Exception:
        return None


async def get_user_display(bot, user_id: int) -> str:
    """Получить имя пользователя для отображения."""
    try:
        user = await bot.get_chat(user_id)
        if user.first_name:
            return f"{user.first_name} (ID: {user_id})"
        return f"User {user_id}"
    except Exception:
        return f"ID {user_id}"


async def get_chat_display(bot, chat_id: int) -> str:
    """Получить название чата для отображения."""
    try:
        chat = await bot.get_chat(chat_id)
        title = chat.title or chat.first_name or str(chat_id)
        return f"{title} (ID: {chat_id})"
    except Exception:
        return f"ID {chat_id}"


def is_admin_or_dev(user_id: int) -> bool:
    return user_id in get_admins() or user_id == config.DEV_ID


# ========== Существующие команды с улучшениями ==========

@rout.event("message",F.text.startswith("/add_admin"))
async def add_admin(message: types.Message):
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    args = message.text.split(maxsplit=2)  # /add_admin user [chat]
    reply = message.reply_to_message
    chat_id = None
    user_id = None
    
    # Если команда в группе, текущий чат используется по умолчанию
    if message.chat.type != "private":
        chat_id = message.chat.id
    # Если в личке, пытаемся получить chat_id из аргументов

    # Обработка аргументов
    if len(args) >= 2:
        # Первый аргумент - пользователь
        user_id = await resolve_user_id(message.bot, args[1])
        if len(args) >= 3:
            # Второй аргумент - чат (если указан)
            chat_id = await resolve_chat_id(message.bot, args[2])
        elif message.chat.type == "private":
            # В личке без указания чата - ошибка
            await message.reply(
                "ℹ️ В личных сообщениях нужно указать chat_id или username чата.\n"
                "Пример: /add_admin @username 123456789"
            )
            return
    elif reply:
        # Если есть reply, берём пользователя из reply
        user_id = reply.from_user.id
        # Если в личке, нужно указать чат отдельно, но можно попросить
        if message.chat.type == "private":
            await message.reply(
                "ℹ️ В личных сообщениях нужно указать chat_id или username чата.\n"
                "Пример: /add_admin (reply на сообщение) 123456789"
            )
            return
    else:
        await message.reply(
            "ℹ️ Используйте: /add_admin [user_id или @username] [chat_id или @chat_username]\n"
            "В группе можно не указывать chat_id – будет добавлен текущий чат.\n"
            "Или ответьте на сообщение пользователя."
        )
        return

    if user_id is None:
        await message.reply("❌ Не удалось определить пользователя. Укажите корректный ID или username.")
        return
    if chat_id is None:
        await message.reply("❌ Не удалось определить чат. Укажите корректный ID или username чата.")
        return

    # Добавляем
    result = add_aid(user_id, chat_id)
    user_display = await get_user_display(message.bot, user_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Admin {user_id} added to chat {chat_id} by {message.from_user.id}")
        await message.answer(f"✅ Админ {user_display} добавлен в чат {chat_display}")
    else:
        await message.answer(f"ℹ️ Админ {user_display} уже управляет чатом {chat_display}")


@rout.event("message",F.text.startswith("/rm_admin"))
async def rm_admin(message: types.Message):
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    args = message.text.split(maxsplit=2)
    reply = message.reply_to_message
    chat_id = None
    user_id = None

    if message.chat.type != "private":
        chat_id = message.chat.id

    if len(args) >= 2:
        user_id = await resolve_user_id(message.bot, args[1])
        if len(args) >= 3:
            chat_id = await resolve_chat_id(message.bot, args[2])
        elif message.chat.type == "private":
            await message.reply(
                "ℹ️ В личных сообщениях нужно указать chat_id или username чата.\n"
                "Пример: /rm_admin @username 123456789"
            )
            return
    elif reply:
        user_id = reply.from_user.id
        if message.chat.type == "private":
            await message.reply(
                "ℹ️ В личных сообщениях нужно указать chat_id или username чата.\n"
                "Пример: /rm_admin (reply) 123456789"
            )
            return
    else:
        await message.reply(
            "ℹ️ Используйте: /rm_admin [user_id или @username] [chat_id или @chat_username]\n"
            "В группе можно не указывать chat_id – будет удалён из текущего чата.\n"
            "Или ответьте на сообщение пользователя."
        )
        return

    if user_id is None:
        await message.reply("❌ Не удалось определить пользователя.")
        return
    if chat_id is None:
        await message.reply("❌ Не удалось определить чат.")
        return

    result = rm_aid(user_id, chat_id)
    user_display = await get_user_display(message.bot, user_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Admin {user_id} removed from chat {chat_id} by {message.from_user.id}")
        await message.answer(f"✅ Админ {user_display} убран из чата {chat_display}")
    else:
        await message.answer(f"ℹ️ Пользователь {user_display} не является админом чата {chat_display}")


@rout.event("message",F.text.startswith("/add_chat"))
async def add_chat(message: types.Message):
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    args = message.text.split(maxsplit=1)
    chat_id = None

    if len(args) >= 2:
        chat_id = await resolve_chat_id(message.bot, args[1])
    elif message.chat.type != "private":
        chat_id = message.chat.id  # текущий чат
    else:
        await message.reply(
            "ℹ️ Используйте: /add_chat [chat_id или @chat_username]\n"
            "В группе можно вызывать без аргументов – будет добавлен текущий чат."
        )
        return

    if chat_id is None:
        await message.reply("❌ Не удалось определить чат.")
        return

    # Проверка прав бота (как было)
    try:
        bot_member = await message.bot.get_chat_member(chat_id, message.bot.id)
    except Exception as e:
        await message.reply(f"❌ Не удалось проверить права бота в чате {chat_id}. Ошибка: {e}")
        return

    if bot_member.status not in ('administrator', 'creator'):
        await message.reply(
            f"❌ Бот не является администратором в чате {chat_id}.\n"
            "Добавьте бота как администратора и повторите."
        )
        return

    # Проверка прав (предупреждение)
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

    result = add_chid(chat_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Chat {chat_id} added to network by {message.from_user.id}")
        await message.answer(f"✅ Чат {chat_display} добавлен в сетку")
    else:
        await message.answer(f"ℹ️ Чат {chat_display} уже в сетке")


@rout.event("message",F.text.startswith("/rm_chat"))
async def rm_chat(message: types.Message):
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    args = message.text.split(maxsplit=1)
    chat_id = None

    if len(args) >= 2:
        chat_id = await resolve_chat_id(message.bot, args[1])
    elif message.chat.type != "private":
        chat_id = message.chat.id
    else:
        await message.reply(
            "ℹ️ Используйте: /rm_chat [chat_id или @chat_username]\n"
            "В группе можно вызывать без аргументов – будет удалён текущий чат."
        )
        return

    if chat_id is None:
        await message.reply("❌ Не удалось определить чат.")
        return

    result = rm_chid(chat_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Chat {chat_id} removed from network by {message.from_user.id}")
        await message.answer(f"✅ Чат {chat_display} убран из сетки")
    else:
        await message.answer(f"ℹ️ Чат {chat_display} не в сетке")


@rout.event("message",F.text.startswith("/get_admins"))
async def get_admins_cmd(message: types.Message):
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    lines = []
    for chat_id, admins in config.ADMIN_IDS.items():
        chat_display = await get_chat_display(message.bot, chat_id)
        lines.append(f"👥 {chat_display}:")
        for i, admin_id in enumerate(admins, 1):
            user_display = await get_user_display(message.bot, admin_id)
            lines.append(f"  {i}. {user_display}")
    result = "\n".join(lines) if lines else "Список администраторов пуст."
    await message.answer(result)


# ========== Новые команды для работы с текущим чатом ==========
@rout.event("message",F.text.startswith("/add_admin_here"))
async def add_admin_here(message: types.Message):
    if message.chat.type == "private":
        await message.reply("❌ Эта команда работает только в группе.")
        return
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    args = message.text.split(maxsplit=1)
    reply = message.reply_to_message
    user_id = None

    if reply:
        user_id = reply.from_user.id
    elif len(args) >= 2:
        user_id = await resolve_user_id(message.bot, args[1])
    else:
        await message.reply(
            "ℹ️ Используйте: /add_admin_here [user_id или @username]\n"
            "или ответьте на сообщение пользователя."
        )
        return

    if user_id is None:
        await message.reply("❌ Не удалось определить пользователя.")
        return

    chat_id = message.chat.id
    result = add_aid(user_id, chat_id)
    user_display = await get_user_display(message.bot, user_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Admin {user_id} added to chat {chat_id} via add_admin_here by {message.from_user.id}")
        await message.answer(f"✅ Админ {user_display} добавлен в чат {chat_display}")
    else:
        await message.answer(f"ℹ️ Админ {user_display} уже управляет чатом {chat_display}")


@rout.event("message",F.text.startswith("/rm_admin_here"))
async def rm_admin_here(message: types.Message):
    if message.chat.type == "private":
        await message.reply("❌ Эта команда работает только в группе.")
        return
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    args = message.text.split(maxsplit=1)
    reply = message.reply_to_message
    user_id = None

    if reply:
        user_id = reply.from_user.id
    elif len(args) >= 2:
        user_id = await resolve_user_id(message.bot, args[1])
    else:
        await message.reply(
            "ℹ️ Используйте: /rm_admin_here [user_id или @username]\n"
            "или ответьте на сообщение пользователя."
        )
        return

    if user_id is None:
        await message.reply("❌ Не удалось определить пользователя.")
        return

    chat_id = message.chat.id
    result = rm_aid(user_id, chat_id)
    user_display = await get_user_display(message.bot, user_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Admin {user_id} removed from chat {chat_id} via rm_admin_here by {message.from_user.id}")
        await message.answer(f"✅ Админ {user_display} убран из чата {chat_display}")
    else:
        await message.answer(f"ℹ️ Пользователь {user_display} не является админом чата {chat_display}")


@rout.event("message",F.text.startswith("/add_this_chat"))
async def add_this_chat(message: types.Message):
    if message.chat.type == "private":
        await message.reply("❌ Эта команда работает только в группе.")
        return
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    chat_id = message.chat.id
    result = add_chid(chat_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Chat {chat_id} added via add_this_chat by {message.from_user.id}")
        await message.answer(f"✅ Чат {chat_display} добавлен в сетку")
    else:
        await message.answer(f"ℹ️ Чат {chat_display} уже в сетке")


@rout.event("message",F.text.startswith("/rm_this_chat"))
async def rm_this_chat(message: types.Message):
    if message.chat.type == "private":
        await message.reply("❌ Эта команда работает только в группе.")
        return
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    chat_id = message.chat.id
    result = rm_chid(chat_id)
    chat_display = await get_chat_display(message.bot, chat_id)
    if result:
        logger.info(f"Chat {chat_id} removed via rm_this_chat by {message.from_user.id}")
        await message.answer(f"✅ Чат {chat_display} убран из сетки")
    else:
        await message.answer(f"ℹ️ Чат {chat_display} не в сетке")


# ========== Справка ==========
@rout.event("message",F.text.startswith("/help_admin"))
async def help_admin(message: types.Message):
    if not is_admin_or_dev(message.from_user.id):
        await message.reply("⛔️ У вас нет прав")
        return

    help_text = """
📚 **Справка по административным командам**

🔹 `/add_admin [user] [chat]` – добавить админа в чат.
   - В группе можно опустить `[chat]` (будет текущий чат).
   - В качестве `[user]` можно указать ID или @username.
   - Можно ответить на сообщение пользователя – тогда `[user]` не нужен.

🔹 `/rm_admin [user] [chat]` – удалить админа из чата (аналогично).

🔹 `/add_chat [chat]` – добавить чат в сетку.
   - В группе можно вызвать без аргументов – добавится текущий чат.
   - Можно указать ID или @username чата.

🔹 `/rm_chat [chat]` – удалить чат из сетки (аналогично).

🔹 `/add_admin_here` – добавить админа в текущий чат (только в группе).
   - Принимает ID или @username, или ответ на сообщение.

🔹 `/rm_admin_here` – удалить админа из текущего чата (только в группе).

🔹 `/add_this_chat` – добавить текущий чат в сетку (только в группе).

🔹 `/rm_this_chat` – удалить текущий чат из сетки (только в группе).

🔹 `/get_admins` – показать всех админов во всех чатах.

🔹 `/help_admin` – эта справка.

💡 **Советы:**
- В группах вы можете просто ответить на сообщение пользователя и использовать команду без указания ID.
"""
    await message.answer(help_text, parse_mode="Markdown")