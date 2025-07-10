import os


class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # API
    API_URL = os.getenv("API_URL", "http://api:8000")
    API_KEY = os.getenv("API_KEY")
    # SQLite DB
    DB_PATH = os.getenv("DB_PATH", "donation.db")
