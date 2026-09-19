import os
from dotenv import load_dotenv
import pickle
from typing import Dict,List
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DEV_ID = int(os.getenv("DEV_ID", 6498513606))
    debug = os.getenv("DEBUG","False").lower() == "true"
    RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", 0.65))
    BAD_WORDS = []
    try:
        with open("bad_words.pkl","rb") as f:
            BAD_WORDS = pickle.load(f)
    except FileNotFoundError:
        pass
    CHATS_IDS = []
    try:
        with open("setka.pkl","rb") as f:
            CHATS_IDS = pickle.load(f)
    except FileNotFoundError:
        pass
    ADMIN_IDS: Dict[int,List] = {} #chat_id,[aids]
    try:
        with open("adm.pkl","rb") as f:
            ADMIN_IDS = pickle.load(f)
    except FileNotFoundError:
        pass
    TRUSTED_MESSAGE_COUNT = 25
    def get_admins(self):
        admins = []
        for j in self.ADMIN_IDS.values():
            for i in j:
                admins.append(i)
        return admins
    # Настройки ML
    ML_THRESHOLD = float(os.getenv("ML_THRESHOLD", 0.5))
    USE_ML = True
    use_onnx = True
    SPAMSHIELD_MODEL_PATH = "./workers/ads_worker/app/shieldmodel"
    def save_bw(self):
        with open("bad_words.pkl","wb") as f:
            pickle.dump(self.BAD_WORDS,f)
    def save_ids(self):
        with open("setka.pkl","wb") as f:
            pickle.dump(self.CHATS_IDS,f)
    def save_aids(self):
        with open("adm.pkl","wb") as f:
            pickle.dump(self.ADMIN_IDS,f)
        
    
config = Config()
def get_admins():
    admins = []
    for j in config.ADMIN_IDS.values():
        for i in j:
            admins.append(i)
    return admins
def add_badword(word: str):
    config.BAD_WORDS.append(word)
    config.save_bw()
def rm_badword(word: str):
    config.BAD_WORDS.remove(word)
    config.save_bw()
def add_chid(id: int):
    if id not in config.CHATS_IDS:
        config.CHATS_IDS.append(id)
        config.save_ids()
        return True
    else:
        return False
def rm_chid(id: int):
    if id in config.CHATS_IDS:
        config.CHATS_IDS.remove(id)
        config.save_ids()
        return True
    else:
        return False
def add_aid(id: int,chat_id: int):
    
    if config.ADMIN_IDS.get(chat_id,None):
        if id not in config.ADMIN_IDS[chat_id]:
            config.ADMIN_IDS[chat_id].append(id)
            config.save_aids()
            return True
        else:
            return False
    else:
        config.ADMIN_IDS[chat_id] = []
    
        config.ADMIN_IDS[chat_id].append(id)
        config.save_aids()
        return True
        
    
def rm_aid(id: int,chat_id: int):
    try:
        config.ADMIN_IDS[chat_id].remove(id)
    except ValueError:
        return False
    config.save_aids()
    return True