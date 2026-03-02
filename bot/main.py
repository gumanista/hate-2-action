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

from pipelines.pipelines import (
    pipeline_process_message,
    pipeline_show_orgs,
    pipeline_change_style,
    pipeline_about_me,
    pipeline_start,
    STYLES,
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_CATEGORY = 1
WAITING_FOR_STYLE = 2

STYLE_LABELS_UA = {
    "polite": "Чемний",
    "funny": "Смішний",
    "sarcastic": "Саркастичний",
    "normal": "Нейтральний",
    "rude": "Грубуватий",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_style_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(STYLE_LABELS_UA.get(s, s.capitalize()), callback_data=f"style:{s}")
        for s in STYLES
    ]
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


def _get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎭 Змінити стиль", callback_data="menu:change_style"),
            InlineKeyboardButton("🏢 Знайти НГО", callback_data="menu:show_orgs"),
        ],
        [InlineKeyboardButton("ℹ️ Про бота", callback_data="menu:about_me")],
    ])


# ── Command Handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        pipeline_start(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_get_start_keyboard(),
    )


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        pipeline_about_me(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if style passed as argument e.g. /style funny
    args = context.args
    if args and args[0].lower() in STYLES:
        user = update.effective_user
        chat = update.effective_chat
        reply = await pipeline_change_style(
            user.id, chat.id, chat.type, requested_style=args[0].lower()
        )
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            "🎭 Обери стиль відповіді:",
            reply_markup=_get_style_keyboard(),
        )


async def cmd_style_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /style_funny, /style_rude, etc."""
    command = update.message.text.lstrip("/").split("@")[0]
    style = command.replace("style_", "")
    if style in STYLES:
        user = update.effective_user
        chat = update.effective_chat
        reply = await pipeline_change_style(
            user.id, chat.id, chat.type, requested_style=style
        )
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


async def cmd_orgs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏢 НГО якої категорії тебе цікавлять?\n\n"
        "Наприклад: освіта, армія, економіка тощо.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_FOR_CATEGORY


async def cmd_orgs_receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    category = update.message.text

    await update.message.reply_text("🔍 Шукаю організації...", parse_mode=ParseMode.MARKDOWN)
    reply = await pipeline_show_orgs(
        user.id, chat.id, chat.type, category, tg_message_id=update.message.message_id
    )
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    return ConversationHandler.END


async def cmd_orgs_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пошук скасовано.")
    return ConversationHandler.END


# ── Callback Query Handler ────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat = update.effective_chat
    data = query.data

    if data.startswith("style:"):
        style = data.split(":")[1]
        reply = await pipeline_change_style(
            user.id, chat.id, chat.type, requested_style=style
        )
        await query.edit_message_text(reply, parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:about_me":
        await query.edit_message_text(pipeline_about_me(), parse_mode=ParseMode.MARKDOWN)

    elif data == "menu:change_style":
        await query.edit_message_text(
            "🎭 Обери бажаний стиль відповіді:",
            reply_markup=_get_style_keyboard(),
        )

    elif data == "menu:show_orgs":
        await query.edit_message_text(
            "🏢 Організації якої категорії тебе цікавлять?\n\n"
            "Відповідай на це повідомлення темою, наприклад: *клімат*, *корупція*, *здоровʼя* тощо.",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["waiting_for_org_category"] = True


# ── Message Handler ───────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = update.effective_user
    chat = update.effective_chat
    text = message.text.strip()
    bot_username = context.bot.username

    # In group chats, only respond when mentioned
    if chat.type in ("group", "supergroup"):
        mentioned = (
            f"@{bot_username}" in text
            or (message.reply_to_message and message.reply_to_message.from_user.username == bot_username)
        )
        if not mentioned:
            return
        text = text.replace(f"@{bot_username}", "").strip()

    # If waiting for org category from inline button flow
    if context.user_data.get("waiting_for_org_category"):
        context.user_data.pop("waiting_for_org_category")
        await message.reply_text("🔍 Шукаю організації...", parse_mode=ParseMode.MARKDOWN)
        reply = await pipeline_show_orgs(
            user.id, chat.id, chat.type, text, tg_message_id=message.message_id
        )
        await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    reply = await pipeline_process_message(
        user.id, chat.id, chat.type, text, tg_message_id=message.message_id
    )
    await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


# ── Error Handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Сталася помилка. Спробуй ще раз пізніше."
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("style", cmd_style))
    for style in STYLES:
        app.add_handler(CommandHandler(f"style_{style}", cmd_style_shortcut))

    # Org search conversation
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

    # Callback queries (inline buttons)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # General message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Starting Hate-2-Action bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
