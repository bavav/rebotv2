import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # ID администратора
    TARGET_USER_ID = int(os.getenv("TARGET_USER_ID", 0))  # Кому пересылать
    
    # RAG настройки
    DEFAULT_THRESHOLD = float(os.getenv("RAG_THRESHOLD", 0.65))
    MAX_MESSAGE_LENGTH = 4096

config = Config()