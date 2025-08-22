import re
import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from .config import Config


logger = logging.getLogger(__name__)


# The available response styles.
RESPONSE_STYLES = ["empathetic", "rude", "formal"]


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
    3) POST to the API.
    4) Send the reply from API back to the user.
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

    # determine response style
    response_style = "empathetic"  # default
    words = cleaned.lower().split()
    if words and words[0] in RESPONSE_STYLES:
        response_style = words[0]
        cleaned = " ".join(words[1:])

    # call the API
    try:
        if not Config.API_KEY:
            logger.error("API_KEY not configured")
            await msg.reply_text("⚠️ API-ключ не налаштовано. Будь ласка, зверніться до адміністратора.")
            return

        headers = {"X-API-Key": Config.API_KEY}
        payload = {"message": cleaned, "response_style": response_style}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.API_URL}/process-message",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
        reply_text = response.json()["text"]
    except httpx.HTTPStatusError as e:
        logger.exception(f"API request failed: {e.response.text}")
        await msg.reply_text("⚠️ Сталася помилка при обробці. Спробуйте пізніше.")
        return
    except Exception:
        logger.exception("API call error")
        await msg.reply_text("⚠️ Сталася помилка при обробці. Спробуйте пізніше.")
        return

    # send the generated reply
    await msg.reply_text(reply_text)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if update and update.effective_message:
        # Send a message to the user
        await update.effective_message.reply_text(
            "⚠️ Сталася помилка при обробці повідомлення. Спробуйте пізніше."
        )
