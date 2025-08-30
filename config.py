import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не знайдено у змінних середовища!")

ADMINS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
if not ADMINS:
    raise ValueError("ADMIN_IDS не знайдено у змінних середовища!")

DB_PATH = os.getenv("DB_PATH", "bot.db")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "10"))
MAX_MESSAGE_LENGTH = 4096
MAX_SEARCH_LENGTH = 100

ALLOWED_ROLES = ["Студент", "Абітурієнт", "Викладач", "Батько"]