import json
import redis.asyncio as redis
from aiogram.types import ChatPermissions
from .app.config import config
# Создаём клиент (подключение берётся из config)
redis_client: redis.Redis = redis.from_url(
    f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
    encoding="utf-8",
    decode_responses=True,
)


RIGHTS_TTL = 36000

def _key(chat_id: int, user_id: int) -> str:
    return f"rights_cache:{chat_id}:{user_id}"

async def save_rights(chat_id: int, user_id: int, permissions: ChatPermissions) -> None:
    """Сохраняет права пользователя в Redis."""
    await redis_client.set(
        _key(chat_id, user_id),
        permissions.model_dump_json(),
        ex=RIGHTS_TTL,
    )

async def pop_rights(chat_id: int, user_id: int) -> ChatPermissions | None:
    """
    Атомарно забирает права из Redis и удаляет запись.
    Возвращает ChatPermissions или None, если записи нет.
    """
    key = _key(chat_id, user_id)
    raw = await redis_client.get(key)
    if raw is None:
        return None
    # Удаляем запись
    await redis_client.delete(key)
    try:
        data = json.loads(raw)
        return ChatPermissions(**data)
    except Exception:
        return None