import os
from typing import Set

BOT_TOKEN = os.getenv("BOT_TOKEN", "8450014507:AAHjNEduFSG6OHHSzik-tJTuqoD58WTmEFI")
ADMIN_IDS: Set[int] = {int(x) for x in os.getenv("ADMIN_IDS", "1051288232").strip().split(",") if x.strip().isdigit()}
DEVELOPER_ID = 1051288232
DB_PATH = "anonimchat.db"  

REACTION_CHOICES = [
    ("👍", "like"),
    ("👎", "dislike"),
    ("⚠️ Пожаловаться", "report"),
]
REPORT_REASONS = [
    ("🚫 Оскорбления", "insults"),
    ("🔞 Неподобающий контент", "inappropriate"),
    ("💼 Реклама/спам", "spam"),
    ("🎭 Неадекватное поведение", "bad_behavior"),
    ("📵 Другое", "other"),
]
