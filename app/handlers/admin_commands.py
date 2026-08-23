from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.services.rag_service import RAGService
from app.services.ml_model import SpamClassifier
from app.config import config
import logging

logger = logging.getLogger(__name__)
router = Router()
rag_service = RAGService()
ml_classifier = SpamClassifier()


from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup

# Фабрика для кнопок главного меню (мут/бан)



# ==================== УПРАВЛЕНИЕ ПРИМЕРАМИ ====================

@router.message(Command("add_white"))
async def add_white_example(message: types.Message):
    """Добавить безопасный пример (НЕ реклама)"""
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    text = message.text.replace("/add_white", "").strip()

    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /add_white [текст]\n"
                "Или ответьте на сообщение с этой командой"
            )
            return

    doc_id = rag_service.add_white_example(text)

    if doc_id:
        stats = rag_service.get_statistics()
        await message.reply(
            f"✅ Безопасный пример добавлен!\n"
            f"📝 ID: {doc_id[:8]}...\n"
            f"📊 Всего безопасных: {stats['white_count']}"
        )
    else:
        await message.reply("❌ Ошибка при добавлении примера")


@router.message(Command("add_black"))
async def add_black_example(message: types.Message):
    """Добавить рекламный пример"""
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return

    text = message.text.replace("/add_black", "").strip()

    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /add_black [текст]\n"
                "Или ответьте на сообщение с этой командой"
            )
            return

    doc_id = rag_service.add_black_example(text)

    if doc_id:
        stats = rag_service.get_statistics()
        await message.reply(
            f"✅ Рекламный пример добавлен!\n"
            f"📝 ID: {doc_id[:8]}...\n"
            f"📊 Всего рекламных: {stats['black_count']}"
        )
    else:
        await message.reply("❌ Ошибка при добавлении примера")


# ==================== УДАЛЕНИЕ ПРИМЕРОВ ====================

@router.message(Command("delete_white"))
async def delete_white_example(message: types.Message):
    """Удалить безопасный пример по тексту"""
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return

    text = message.text.replace("/delete_white", "").strip()

    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /delete_white [текст]\n"
                "Или ответьте на сообщение с этой командой"
            )
            return

    matches = rag_service.find_white_by_text(text)

    if not matches:
        await message.reply(
          f"❌ Не найдено безопасных примеров с текстом:\n`{text[:100]}`")
        return

    preview = "\n".join([f"• {m['text'][:60]}..." for m in matches[:5]])
    if len(matches) > 5:
        preview += f"\n... и еще {len(matches) - 5} примеров"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
          text="✅ Да, удалить",
          callback_data=f"confirm_delete_white_{text[:50]}")],
        [InlineKeyboardButton(
          text="❌ Отмена",
          callback_data="cancel_delete")]
    ])

    await message.reply(
        f"⚠️ Найдено {len(matches)} примеров для удаления:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Удалить все эти примеры?",
        reply_markup=keyboard
    )


@router.message(Command("delete_black"))
async def delete_black_example(message: types.Message):
    """Удалить рекламный пример по тексту"""
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return

    text = message.text.replace("/delete_black", "").strip()

    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply(
                "ℹ️ Используйте: /delete_black [текст]\n"
                "Или ответьте на сообщение с этой командой"
            )
            return

    matches = rag_service.find_black_by_text(text)

    if not matches:
        await message.reply(
          f"❌ Не найдено рекламных примеров с текстом:\n`{text[:100]}`")
        return

    preview = "\n".join([f"• {m['text'][:60]}..." for m in matches[:5]])
    if len(matches) > 5:
        preview += f"\n... и еще {len(matches) - 5} примеров"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
          text="✅ Да, удалить",
          callback_data=f"confirm_delete_black_{text[:50]}"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")]
    ])

    await message.reply(
        f"⚠️ Найдено {len(matches)} примеров для удаления:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Удалить все эти примеры?",
        reply_markup=keyboard
    )


# ==================== ПОИСК И ПРОСМОТР ====================

@router.message(Command("find_white"))
async def find_white_example(message: types.Message):
    """Найти безопасные примеры по тексту"""
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return

    text = message.text.replace("/find_white", "").strip()

    if not text:
        await message.reply("ℹ️ Используйте: /find_white [текст]")
        return

    matches = rag_service.find_white_by_text(text)

    if not matches:
        await message.reply(
          f"❌ Не найдено безопасных примеров с текстом:\n`{text[:100]}`"
        )
        return

    result = f"🔍 Найдено {len(matches)} безопасных примеров:\n━━━━━━━━━━━━━━━━\n"
    for i, match in enumerate(matches[:10], 1):

        result += f"{i}.{match['text'][:100]}\n"
        result += f"   📊 Сходство: {1 - match['distance']:.3f}\n"
        result += f"   🆔 ID: {match['id'][:8]}...\n\n"

    if len(matches) > 10:
        result += f"... и еще {len(matches) - 10} примеров"

    await message.reply(result)


@router.message(Command("find_black"))
async def find_black_example(message: types.Message):
    """Найти рекламные примеры по тексту"""
    if message.from_user.id not in config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return

    text = message.text.replace("/find_black", "").strip()

    if not text:
        await message.reply("ℹ️ Используйте: /find_black [текст]")
        return

    matches = rag_service.find_black_by_text(text)
    
    if not matches:
        await message.reply(f"❌ Не найдено рекламных примеров с текстом:\n`{text[:100]}`")
        return
    
    result = f"🔍 Найдено {len(matches)} рекламных примеров:\n━━━━━━━━━━━━━━━━\n"
    for i, match in enumerate(matches[:10], 1):
        result += f"{i}. {match['text'][:100]}\n"
        result += f"   📊 Сходство: {1 - match['distance']:.3f}\n"
        result += f"   🆔 ID: {match['id'][:8]}...\n\n"
    
    if len(matches) > 10:
        result += f"... и еще {len(matches) - 10} примеров"
    
    await message.reply(result)


@router.message(Command("list_white"))
async def list_white_examples(message: types.Message):
    """Показать список безопасных примеров"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    parts = message.text.split()
    limit = 20
    if len(parts) > 1:
        try:
            limit = int(parts[1])
            limit = min(limit, 50)
        except:
            pass
    
    examples = rag_service.list_white_examples(limit)
    
    if not examples:
        await message.reply("📭 Нет безопасных примеров в базе")
        return
    
    result = f"📋 Безопасные примеры ({len(examples)}):\n━━━━━━━━━━━━━━━━\n"
    for i, ex in enumerate(examples, 1):
        result += f"{i}. {ex['text'][:80]}\n"
        result += f"   🆔 {ex['id'][:8]}...\n\n"
    
    await message.reply(result)


@router.message(Command("list_black"))
async def list_black_examples(message: types.Message):
    """Показать список рекламных примеров"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    parts = message.text.split()
    limit = 20
    if len(parts) > 1:
        try:
            limit = int(parts[1])
            limit = min(limit, 50)
        except:
            pass
    
    examples = rag_service.list_black_examples(limit)
    
    if not examples:
        await message.reply("📭 Нет рекламных примеров в базе")
        return
    
    result = f"📋 Рекламные примеры ({len(examples)}):\n━━━━━━━━━━━━━━━━\n"
    for i, ex in enumerate(examples, 1):
        result += f"{i}. {ex['text'][:80]}\n"
        result += f"   🆔 {ex['id'][:8]}...\n\n"
    
    await message.reply(result)


# ==================== УПРАВЛЕНИЕ ML МОДЕЛЬЮ ====================

@router.message(Command("set_model"))
async def set_model(message: types.Message):
    """Изменить ML-модель"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        models = ml_classifier.get_available_models()
        await message.reply(
            f"ℹ️ Используйте: /set_model [имя_модели]\n\n"
            f"Доступные модели:\n" + 
            "\n".join([f"• {m}" for m in models])
        )
        return
    
    model_name = parts[1]
    loading_msg = await message.reply(f"🔄 Загрузка модели: {model_name}...")
    
    success = ml_classifier.load_model(model_name)
    
    if success:
        await loading_msg.edit_text(
            f"✅ Модель успешно загружена!\n"
            f"📊 Текущая модель: {model_name}\n"
            f"🎯 Порог: {ml_classifier.threshold:.2f}"
        )
    else:
        await loading_msg.edit_text(
            f"❌ Не удалось загрузить модель: {model_name}\n"
            f"Текущая модель: {ml_classifier.model_name}"
        )


@router.message(Command("set_ml_threshold"))
async def set_ml_threshold(message: types.Message):
    """Установить порог ML-модели"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError
        threshold = float(parts[1])
        
        if not (0 <= threshold <= 1):
            await message.reply("❌ Порог должен быть от 0 до 1")
            return
        
        ml_classifier.set_threshold(threshold)
        await message.reply(
            f"✅ Порог ML-модели установлен: {threshold:.2f}\n"
            f"ℹ️ Текущая модель: {ml_classifier.model_name}"
        )
        
    except (ValueError, IndexError):
        await message.reply(
            "❌ Неверный формат\n"
            "Используйте: /set_ml_threshold 0.5"
        )


@router.message(Command("set_templates"))
async def set_templates(message: types.Message):
    """Изменить шаблоны для ML-модели"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/set_templates", "").strip()
    
    if not text or '|' not in text:
        await message.reply(
            "ℹ️ Используйте: /set_templates [спам_шаблон] | [безопасный_шаблон]\n\n"
            "Пример:\n"
            "/set_templates реклама спам предложение | привет общение нормально"
        )
        return
    
    parts = text.split('|')
    if len(parts) != 2:
        await message.reply("❌ Должно быть 2 шаблона")
        return
    
    spam_template = parts[0].strip()
    safe_template = parts[1].strip()
    
    ml_classifier.set_templates(spam_template, safe_template)
    
    await message.reply(
        f"✅ Шаблоны обновлены:\n"
        f"🔴 Спам: {spam_template[:50]}...\n"
        f"🟢 Безопасно: {safe_template[:50]}..."
    )


@router.message(Command("ml_stats"))
async def ml_stats(message: types.Message):
    """Показать статистику ML-модели"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    stats = rag_service.get_statistics()
    
    await message.reply(
        f"🤖 ML-модель:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 Модель: {ml_classifier.model_name}\n"
        f"🎯 Порог: {ml_classifier.threshold:.2f}\n"
        f"📱 Устройство: {ml_classifier.device}\n"
        f"🔴 Шаблон спама: {ml_classifier.spam_template[:50]}...\n"
        f"🟢 Шаблон безопасно: {ml_classifier.safe_template[:50]}...\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 RAG-статистика:\n"
        f"🟢 Безопасных: {stats['white_count']}\n"
        f"🔴 Рекламных: {stats['black_count']}\n"
        f"📚 Всего: {stats['total']}"
    )


@router.message(Command("toggle_ml"))
async def toggle_ml(message: types.Message):
    """Включить/выключить ML-проверку"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    rag_service.use_ml = not rag_service.use_ml
    status = "✅ ВКЛЮЧЕНА" if rag_service.use_ml else "❌ ВЫКЛЮЧЕНА"
    
    await message.reply(
        f"🔄 ML-проверка: {status}\n"
        f"ℹ️ RAG-проверка всегда активна"
    )


# ==================== ПРОВЕРКА И СТАТИСТИКА ====================

@router.message(Command("check"))
async def check_text(message: types.Message):
    """Проверить текст с подробным выводом"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    text = message.text.replace("/check", "").strip()
    
    if not text:
        if message.reply_to_message and message.reply_to_message.text:
            text = message.reply_to_message.text
        else:
            await message.reply("ℹ️ Используйте: /check [текст]")
            return
    
    is_ad, confidence, method, closest_white, closest_black = rag_service.check_advertisement(text)
    
    method_emoji = {
        "rag_spam_dominates": "⚡",
        "rag_spam_detected": "⚡",
        "rag_safe_dominates": "🟢",
        "rag_safe_detected": "🟢",
        "rag_no_match": "❓",
        "ml_classifier": "🧠",
        "rag_spam_in_doubt": "⚡"
    }.get(method, "❓")
    
    result_text = (
        f"🔍 Результат проверки:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 Текст: {text[:50]}...\n"
        f"{'🔴 РЕКЛАМА' if is_ad else '🟢 НЕ РЕКЛАМА'}\n"
        f"📊 Уверенность: {confidence:.2f}\n"
        f"🔬 Метод: {method_emoji} {method}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🟢 Ближайший безопасный:\n{closest_white[:50] if closest_white else '❌ Нет'}\n"
        f"🔴 Ближайший рекламный:\n{closest_black[:50] if closest_black else '❌ Нет'}"
    )
    
    await message.reply(result_text)


@router.message(Command("stats"))
async def get_stats(message: types.Message):
    """Показать общую статистику"""
    if message.from_user.id not in  config.ADMIN_ID:
        await message.reply("⛔️ У вас нет прав")
        return
    
    stats = rag_service.get_statistics()
    
    await message.reply(
        f"📊 Общая статистика:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🟢 Безопасных примеров: {stats['white_count']}\n"
        f"🔴 Рекламных примеров: {stats['black_count']}\n"
        f"📚 Всего примеров: {stats['total']}\n"
        f"🧠 ML-проверка: {'ВКЛ' if rag_service.use_ml else 'ВЫКЛ'}\n"
        f"🎯 Порог ML: {ml_classifier.threshold:.2f}"
    )


# ==================== CALLBACK-ОБРАБОТЧИКИ ====================

@router.callback_query(F.data.startswith("confirm_delete_white_"))
async def confirm_delete_white(callback: types.CallbackQuery):
    """Подтверждение удаления из белой коллекции"""
    text = callback.data.replace("confirm_delete_white_", "")
    count, texts = rag_service.delete_white_by_text(text)
    
    if count > 0:
        await callback.message.edit_text(
            f"✅ Удалено {count} безопасных примеров:\n"
            f"━━━━━━━━━━━━━━━━\n"
            + "\n".join([f"• {t[:60]}..." for t in texts[:5]])
            + (f"\n... и еще {len(texts) - 5}" if len(texts) > 5 else "")
        )
    else:
        await callback.message.edit_text("❌ Не удалось удалить примеры")
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_black_"))
async def confirm_delete_black(callback: types.CallbackQuery):
    """Подтверждение удаления из черной коллекции"""
    text = callback.data.replace("confirm_delete_black_", "")
    count, texts = rag_service.delete_black_by_text(text)
    
    if count > 0:
        await callback.message.edit_text(
            f"✅ Удалено {count} рекламных примеров:\n"
            f"━━━━━━━━━━━━━━━━\n"
            + "\n".join([f"• {t[:60]}..." for t in texts[:5]])
            + (f"\n... и еще {len(texts) - 5}" if len(texts) > 5 else "")
        )
    else:
        await callback.message.edit_text("❌ Не удалось удалить примеры")
    
    await callback.answer()


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    """Отмена удаления"""
    await callback.message.edit_text("❌ Удаление отменено")
    await callback.answer()


