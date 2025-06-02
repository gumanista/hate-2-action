import os

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # SQLite DB
    DB_PATH = os.getenv("DB_PATH", "donation.db")
