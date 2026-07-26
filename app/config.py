import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = [int(os.getenv("ADMIN_ID", 0))]
    TARGET_USER_ID = int(os.getenv("TARGET_USER_ID", 0))
    RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", 0.65))
    with open("admins_ids.txt",mode="r") as f:
        ADMIN_ID.append(str(f.read()).splitlines())
    
    # Настройки ML
    ML_THRESHOLD = 0.5
    USE_ML = True
    def add_admin(ids: list):
        ADMIN_ID.append(ids)
        with open("admins_ids.txt",a) as f:
            f.writelines(ids)

config = Config()