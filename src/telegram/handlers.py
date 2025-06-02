import re
import logging
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from src.pipeline import process_message
from .config import Config

logger = logging.getLogger(__name__)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with a hello and instructions."""
    await update.message.reply_text(
        f"👋 Привіт! Щоб я відповів, згадай мене з ключовим словом, наприклад "
        f"'@{ctx.bot.username} help'."
    )

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    1) Check that the bot was mentioned.
    2) Strip out the mention.
    3) Insert into messages table.
    4) Run pipeline.process_message to get the real reply.
    5) Send it back.
    """
    msg = update.message
    if not msg or not msg.text:
        return

    bot_username = ctx.bot.username.lower()
    text = msg.text.strip()

    # only handle when bot is mentioned
    if f"@{bot_username}" not in text.lower():
        return

    # strip all @mentions (including ours) and normalize
    cleaned = re.sub(r"@\w+", "", text).strip()

    # persist incoming message
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cur = conn.cursor()
        user_id = msg.from_user.id
        user_username = msg.from_user.username or f"user_{user_id}"
        chat_title = None if msg.chat.type == 'private' else msg.chat.title
        cur.execute(
            "INSERT INTO messages (user_id, user_username, chat_title, text) "
            "VALUES (?, ?, ?, ?)",
            (user_id, user_username, chat_title, cleaned)
        )
        message_id = cur.lastrowid
        conn.commit()
    except sqlite3.Error as e:
        logger.error("DB insert failed: %s", e)
        await msg.reply_text("⚠️ Вибачте, не вдалось зберегти повідомлення.")
        return
    finally:
        conn.close()

    # run the 3-stage pipeline
    try:
        reply_text = process_message(message_id, db_file=Config.DB_PATH)
    except Exception as e:
        logger.exception("Pipeline error")
        await msg.reply_text("⚠️ Сталася помилка при обробці. Спробуйте пізніше.")
        return

    # send the generated reply
    await msg.reply_text(reply_text)

def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Log exceptions."""
    logger.error("Update %r caused error %r", update, ctx.error)
