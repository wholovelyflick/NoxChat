import os
from typing import Set

BOT_TOKEN = os.getenv("BOT_TOKEN", "8333752229:AAF3Imqc-k-vaWvn7wMRMu6Tx0YoWEf1J5c")
ADMIN_IDS: Set[int] = {int(x) for x in os.getenv("ADMIN_IDS", "1051288232").strip().split(",") if x.strip().isdigit()}
DEVELOPER_ID = 1051288232
DB_PATH = "anonimchat.db"  


GITHUB_TOKEN = "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"
GITHUB_REPO_OWNER = "wholovelyflick"
GITHUB_REPO_NAME = "NoxChat"
GITHUB_DB_FILE = "db.txt"

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