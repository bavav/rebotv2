# storage.py
from datetime import datetime, date
from typing import Dict, Tuple, Optional
import secrets

# Значение: (user_id, msg_id, chat_id, day_str)
pending_globan: Dict[str, Tuple[int, int, int, str]] = {}

def generate_key() -> str:
    return secrets.token_hex(3)  # 6 символов

def add_globan_data(user_id: int, msg_id: int, chat_id: int) -> str:
    """Добавляет запись и возвращает ключ."""
    key = generate_key()
    today_str = date.today().isoformat()  # '2026-08-28'
    pending_globan[key] = (user_id, msg_id, chat_id, today_str)
    return key

def get_globan_data(key: str) -> Optional[Tuple[int, int, int]]:
    """Возвращает данные, если они не устарели (созданы сегодня), иначе удаляет."""
    data = pending_globan.get(key, None)
    if data is None:
        return None
    user_id, msg_id, chat_id, day_str = data
    if day_str == date.today().isoformat():
        return (user_id, msg_id, chat_id)
    # Если день не совпадает — игнорируем (данные уже удалены из словаря)
    return None

def endget_globan_data(key: str) -> Optional[Tuple[int, int, int]]:
    """Возвращает данные, если они не устарели (созданы сегодня), иначе удаляет."""
    data = pending_globan.pop(key, None)
    if data is None:
        return None
    user_id, msg_id, chat_id, day_str = data
    if day_str == date.today().isoformat():
        return (user_id, msg_id, chat_id)
    # Если день не совпадает — игнорируем (данные уже удалены из словаря)
    return None