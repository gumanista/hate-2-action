"""
Telegram bot entrypoint.

Purpose:
- Configure Telegram handlers and route user interactions into pipeline layer.

Main responsibilities:
1. Initialize environment, logging, and bot application.
2. Expose command handlers (`/start`, `/about`, `/style`, `/orgs`, style shortcuts).
3. Handle inline keyboard callbacks.
4. Process plain text messages and forward them to orchestrator pipelines.
5. Handle runtime exceptions and run polling loop.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

from pipelines import (
    pipeline_process_message,
    STYLES,
    STYLE_LABELS_UA,
)
from db import queries
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WAITING_FOR_CATEGORY = 1
WAITING_FOR_STYLE = 2
ORG_SEARCH_PROMPT = (
    "🏢 Яку тему або категорію організацій шукаєш?\n\n"
    "Напиши, наприклад: корупція, права тварин, освіта, здоровʼя."
)

REQUIRED_ENV_VARS = (
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
)


def _get_run_mode() -> str:
    configured_mode = os.getenv("APP_MODE")
    if configured_mode:
        return configured_mode.strip().lower()

    if os.getenv("K_SERVICE") or os.getenv("WEBHOOK_URL"):
        return "webhook"

    return "polling"


def _get_webhook_config() -> tuple[int, str, str, str | None]:
    port = int(os.getenv("PORT", "8080"))
    base_url = os.getenv("WEBHOOK_URL")
    if not base_url:
        raise ValueError("WEBHOOK_URL environment variable not set for webhook mode")

    webhook_path = os.getenv("TELEGRAM_WEBHOOK_PATH", "telegram/webhook").strip("/")
    if not webhook_path:
        raise ValueError("TELEGRAM_WEBHOOK_PATH must not be empty")

    webhook_url = f"{base_url.rstrip('/')}/{webhook_path}"
    secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    return port, webhook_path, webhook_url, secret_token


def _get_style_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            STYLE_LABELS_UA.get(s, s.capitalize()), callback_data=f"style:{s}"
        )
        for s in STYLES
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


def _get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎭 Змінити стиль", callback_data="menu:change_style"),
                InlineKeyboardButton("🏢 Знайти НГО", callback_data="menu:show_orgs"),
            ],
            [InlineKeyboardButton("ℹ️ Про бота", callback_data="menu:about_me")],
        ]
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    user = update.effective_user
    chat = update.effective_chat
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        "/start",
        tg_message_id=update.message.message_id,
        forced_pipeline="start",
    )
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_get_start_keyboard(),
    )


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    user = update.effective_user
    chat = update.effective_chat
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        "/about",
        tg_message_id=update.message.message_id,
        forced_pipeline="about_me",
    )
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    args = context.args
    if args and args[0].lower() in STYLES:
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            f"/style_{args[0].lower()}",
            tg_message_id=update.message.message_id,
            forced_pipeline="change_style",
        )
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    else:
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            "/style",
            tg_message_id=update.message.message_id,
            forced_pipeline="change_style",
        )
        await update.message.reply_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_get_style_keyboard(),
        )


async def cmd_style_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /style_funny, /style_rude, etc."""
    _ = context
    command = update.message.text.lstrip("/").split("@")[0]
    style = command.replace("style_", "")
    if style in STYLES:
        user = update.effective_user
        chat = update.effective_chat
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            update.message.text,
            tg_message_id=update.message.message_id,
            forced_pipeline="change_style",
        )
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


async def cmd_orgs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    user = update.effective_user
    chat = update.effective_chat
    queries.get_or_create_user(user.id)
    queries.get_or_create_chat(chat.id, chat.type)
    queries.save_message(
        chat.id,
        user.id,
        "/orgs",
        ORG_SEARCH_PROMPT,
        tg_message_id=update.message.message_id,
        pipeline_used="show_orgs",
    )
    await update.message.reply_text(
        ORG_SEARCH_PROMPT,
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_FOR_CATEGORY


async def cmd_orgs_receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    user = update.effective_user
    chat = update.effective_chat
    category = update.message.text

    await update.message.reply_text("🔍 Шукаю організації...", parse_mode=ParseMode.MARKDOWN)
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        category,
        tg_message_id=update.message.message_id,
    )
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
    return ConversationHandler.END


async def cmd_orgs_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = context
    await update.message.reply_text("Пошук скасовано.")
    return ConversationHandler.END


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat = update.effective_chat
    data = query.data

    if data.startswith("style:"):
        style = data.split(":")[1]
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            f"/style_{style}",
            tg_message_id=query.message.message_id if query.message else None,
            forced_pipeline="change_style",
        )
        await query.edit_message_text(reply, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:about_me":
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            "/about",
            tg_message_id=query.message.message_id if query.message else None,
            forced_pipeline="about_me",
        )
        await query.edit_message_text(reply, parse_mode=ParseMode.MARKDOWN)
    elif data == "menu:change_style":
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            "/style",
            tg_message_id=query.message.message_id if query.message else None,
            forced_pipeline="change_style",
        )
        await query.edit_message_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_get_style_keyboard(),
        )
    elif data == "menu:show_orgs":
        queries.get_or_create_user(user.id)
        queries.get_or_create_chat(chat.id, chat.type)
        queries.save_message(
            chat.id,
            user.id,
            "/orgs",
            ORG_SEARCH_PROMPT,
            tg_message_id=query.message.message_id if query.message else None,
            pipeline_used="show_orgs",
        )
        await query.edit_message_text(
            ORG_SEARCH_PROMPT,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["waiting_for_org_category"] = True
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return
    user = update.effective_user
    chat = update.effective_chat
    text = message.text.strip()
    bot_username = context.bot.username
    if chat.type in ("group", "supergroup"):
        mentioned = (
            f"@{bot_username}" in text
            or (
                message.reply_to_message
                and message.reply_to_message.from_user.username == bot_username
            )
        )
        if not mentioned:
            return
        text = text.replace(f"@{bot_username}", "").strip()
    if context.user_data.get("waiting_for_org_category"):
        context.user_data.pop("waiting_for_org_category")
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            text,
            tg_message_id=message.message_id,
        )
        await message.reply_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return
    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    reply = await pipeline_process_message(
        user.id, chat.id, chat.type, text, tg_message_id=message.message_id
    )
    await message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Сталася помилка. Спробуй ще раз пізніше."
        )


def _validate_required_env() -> None:
    missing_vars = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing_vars:
        missing_list = ", ".join(sorted(missing_vars))
        raise ValueError(f"Missing required environment variables: {missing_list}")


def main():
    _validate_required_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("style", cmd_style))
    
    for style in STYLES:
        app.add_handler(CommandHandler(f"style_{style}", cmd_style_shortcut))

    org_conv = ConversationHandler(
        entry_points=[CommandHandler("orgs", cmd_orgs_start)],
        states={
            WAITING_FOR_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_orgs_receive_category)
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_orgs_cancel)],
        per_message=False,
    )
    app.add_handler(org_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    run_mode = _get_run_mode()

    if run_mode == "webhook":
        port, webhook_path, webhook_url, secret_token = _get_webhook_config()
        logger.info(
            "Starting Hate-2-Action bot in webhook mode on port %s with path /%s",
            port,
            webhook_path,
        )
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=webhook_path,
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            secret_token=secret_token,
        )
        return

    logger.info("Starting Hate-2-Action bot in polling mode...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
if __name__ == "__main__":
    main()
