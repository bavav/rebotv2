# load_dataset.py
from datasets import load_dataset
from app.services.vector_store import VectorStore
import logging

# Настройка логирования для отслеживания прогресса
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_ruspam_dataset():
    """
    Загружает датасет russian-spam-detection и добавляет его в векторное хранилище.
    """
    logging.info("Начинаю загрузку датасета 'ruSpamModels/russian-spam-detection'...")

    try:
        # Загрузка датасета. Если требуется авторизация, добавьте параметр `token=True`
        # или передайте свой токен: `token="hf_your_token_here"`
        dataset = load_dataset("ruSpamModels/russian-spam-detection", split="train")
        logging.info(f"Датасет загружен. Всего записей: {len(dataset)}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке датасета: {e}")
        logging.error("Убедитесь, что вы авторизованы на Hugging Face (используйте 'huggingface-cli login')")
        return

    # Инициализация хранилища (создаст коллекции, если их нет)
    vector_store = VectorStore()
    logging.info("Хранилище инициализировано.")

    # Счетчики для отслеживания
    white_count = 0
    black_count = 0
    error_count = 0

    # Итерация по датасету
    for i, example in enumerate(dataset):
        text = example.get('message')
        label = example.get('label')

        # Проверка на валидность данных
        if not text or not isinstance(text, str) or label is None:
            logging.warning(f"Пропуск записи {i}: некорректные данные (text='{text}', label={label})")
            continue

        try:
            if label == 0:
                # Добавляем как безопасное сообщение
                vector_store.add_white_example(text, metadata={"source": "ruSpam_dataset"})
                white_count += 1
            elif label == 1:
                # Добавляем как спам/рекламу
                vector_store.add_black_example(text, metadata={"source": "ruSpam_dataset"})
                black_count += 1
            else:
                logging.warning(f"Пропуск записи {i}: неизвестная метка label={label}")
                continue

            # Логирование прогресса каждые 1000 записей
            if (white_count + black_count) % 1000 == 0:
                logging.info(f"Обработано записей: {white_count + black_count} (Белых: {white_count}, Черных: {black_count})")

        except Exception as e:
            logging.error(f"Ошибка при добавлении записи {i} (text='{text[:50]}...'): {e}")
            error_count += 1

    # Итоговая статистика
    logging.info("="*50)
    logging.info("ЗАВЕРШЕНО ДОБАВЛЕНИЕ ДАТАСЕТА")
    logging.info(f"Успешно добавлено безопасных (white): {white_count}")
    logging.info(f"Успешно добавлено спам (black): {black_count}")
    logging.info(f"Пропущено с ошибками: {error_count}")
    logging.info(f"Всего в хранилище: {vector_store.get_stats()}")
    logging.info("="*50)

if __name__ == "__main__":
    load_ruspam_dataset()