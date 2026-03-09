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

from pipelines import (
    pipeline_process_message,
    STYLES,
    STYLE_LABELS_UA,
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation state id used when waiting for user category in `/orgs` flow.
WAITING_FOR_CATEGORY = 1
# Reserved state id for style flow (currently not used by ConversationHandler).
WAITING_FOR_STYLE = 2


# Build inline keyboard with style buttons (3 buttons per row).
def _get_style_keyboard() -> InlineKeyboardMarkup:
    # Create one button per style with callback payload `style:<style>`.
    buttons = [
        InlineKeyboardButton(
            STYLE_LABELS_UA.get(s, s.capitalize()), callback_data=f"style:{s}"
        )
        for s in STYLES
    ]
    # Split flat button list into rows of at most 3 buttons.
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    # Return Telegram inline keyboard object.
    return InlineKeyboardMarkup(rows)


# Build start menu keyboard shown with `/start`.
def _get_start_keyboard() -> InlineKeyboardMarkup:
    # Return two-row menu: style/orgs in first row, about in second row.
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎭 Змінити стиль", callback_data="menu:change_style"),
                InlineKeyboardButton("🏢 Знайти НГО", callback_data="menu:show_orgs"),
            ],
            [InlineKeyboardButton("ℹ️ Про бота", callback_data="menu:about_me")],
        ]
    )


# Handle `/start` command.
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # `context` is unused in this handler but kept for framework signature compatibility.
    _ = context
    # Extract current user object from update.
    user = update.effective_user
    # Extract current chat object from update.
    chat = update.effective_chat
    # Delegate command handling to orchestrator.
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        "/start",
        tg_message_id=update.message.message_id,
        forced_pipeline="start",
    )
    # Send start text with Markdown and start menu keyboard.
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_get_start_keyboard(),
    )


# Handle `/about` command.
async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # `context` is unused in this handler but kept for framework signature compatibility.
    _ = context
    # Extract current user object from update.
    user = update.effective_user
    # Extract current chat object from update.
    chat = update.effective_chat
    # Delegate command handling to orchestrator.
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        "/about",
        tg_message_id=update.message.message_id,
        forced_pipeline="about_me",
    )
    # Send about text.
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
    )


# Handle `/style` command (with optional argument).
async def cmd_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract current user object from update.
    user = update.effective_user
    # Extract current chat object from update.
    chat = update.effective_chat
    # Read command arguments, e.g. `/style funny` -> ["funny"].
    args = context.args
    # If first arg is valid style, apply it directly.
    if args and args[0].lower() in STYLES:
        # Delegate style update to orchestrator.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            f"/style_{args[0].lower()}",
            tg_message_id=update.message.message_id,
            forced_pipeline="change_style",
        )
        # Send pipeline response to user.
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    else:
        # Delegate style options response to orchestrator.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            "/style",
            tg_message_id=update.message.message_id,
            forced_pipeline="change_style",
        )
        # If no valid style arg, send text plus inline keyboard.
        await update.message.reply_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_get_style_keyboard(),
        )


# Handle shortcut commands like `/style_funny`.
async def cmd_style_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /style_funny, /style_rude, etc."""
    # `context` is unused in this handler but kept for framework signature compatibility.
    _ = context
    # Normalize command token by removing leading `/` and bot mention suffix.
    command = update.message.text.lstrip("/").split("@")[0]
    # Convert `style_funny` command name into `funny` style id.
    style = command.replace("style_", "")
    # Continue only for known style values.
    if style in STYLES:
        # Extract user object.
        user = update.effective_user
        # Extract chat object.
        chat = update.effective_chat
        # Apply style through orchestrator.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            update.message.text,
            tg_message_id=update.message.message_id,
            forced_pipeline="change_style",
        )
        # Return confirmation text from pipeline.
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


# Start `/orgs` conversation by asking user for category.
async def cmd_orgs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract user object for pipeline context.
    user = update.effective_user
    # Extract chat object for pipeline context.
    chat = update.effective_chat
    # Delegate command to orchestrator, which returns clarification prompt.
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        "/orgs",
        tg_message_id=update.message.message_id,
        forced_pipeline="show_orgs",
    )
    # Prompt user to provide a category/topic.
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
    )
    # Move conversation to category-waiting state.
    return WAITING_FOR_CATEGORY


# Receive category text in `/orgs` conversation flow.
async def cmd_orgs_receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # `context` is unused in this handler but kept for framework signature compatibility.
    _ = context
    # Extract user object for pipeline context.
    user = update.effective_user
    # Extract chat object for pipeline context.
    chat = update.effective_chat
    # Extract user-provided category text.
    category = update.message.text

    # Inform user that semantic search is in progress.
    await update.message.reply_text("🔍 Шукаю організації...", parse_mode=ParseMode.MARKDOWN)
    # Delegate category search to orchestrator.
    reply = await pipeline_process_message(
        user.id,
        chat.id,
        chat.type,
        category,
        tg_message_id=update.message.message_id,
        forced_pipeline="show_orgs",
    )
    # Send resulting recommendations.
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
    # End conversation after handling one category input.
    return ConversationHandler.END


# Cancel `/orgs` conversation.
async def cmd_orgs_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # `context` is unused in this handler but kept for framework signature compatibility.
    _ = context
    # Notify user that interactive flow was canceled.
    await update.message.reply_text("Пошук скасовано.")
    # Explicitly end conversation.
    return ConversationHandler.END


# Handle inline keyboard callback queries.
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Read callback query object from update.
    query = update.callback_query
    # Acknowledge callback to stop Telegram client loading state.
    await query.answer()
    # Extract user object.
    user = update.effective_user
    # Extract chat object.
    chat = update.effective_chat
    # Read callback payload string.
    data = query.data

    # Style selection callbacks: `style:<style>`.
    if data.startswith("style:"):
        # Parse style id from callback payload.
        style = data.split(":")[1]
        # Apply style update through orchestrator.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            f"/style_{style}",
            tg_message_id=query.message.message_id if query.message else None,
            forced_pipeline="change_style",
        )
        # Replace original message text with confirmation reply.
        await query.edit_message_text(reply, parse_mode=ParseMode.MARKDOWN)

    # About menu callback.
    elif data == "menu:about_me":
        # Replace message with orchestrator-provided about text.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            "/about",
            tg_message_id=query.message.message_id if query.message else None,
            forced_pipeline="about_me",
        )
        await query.edit_message_text(reply, parse_mode=ParseMode.MARKDOWN)

    # Change-style menu callback.
    elif data == "menu:change_style":
        # Replace message with style chooser text produced by orchestrator.
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

    # Show-orgs menu callback.
    elif data == "menu:show_orgs":
        # Ask user for category in follow-up message using orchestrator prompt.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            "/orgs",
            tg_message_id=query.message.message_id if query.message else None,
            forced_pipeline="show_orgs",
        )
        await query.edit_message_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
        )
        # Set a user-level flag to treat next text as organization category query.
        context.user_data["waiting_for_org_category"] = True


# Handle general text messages that are not slash commands.
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract message object from update.
    message = update.message
    # Ignore updates without text payload.
    if not message or not message.text:
        # Exit early for non-text events.
        return

    # Extract user object for pipeline context.
    user = update.effective_user
    # Extract chat object for pipeline context.
    chat = update.effective_chat
    # Normalize message text by trimming leading/trailing whitespace.
    text = message.text.strip()
    # Read current bot username for mention checks in group chats.
    bot_username = context.bot.username

    # In group chats, reply only when bot is mentioned or message replies to bot.
    if chat.type in ("group", "supergroup"):
        # Detect explicit @mention or direct reply to the bot's message.
        mentioned = (
            f"@{bot_username}" in text
            or (
                message.reply_to_message
                and message.reply_to_message.from_user.username == bot_username
            )
        )
        # Ignore message when bot is not addressed in group context.
        if not mentioned:
            # Exit without response.
            return
        # Remove mention token before sending text to pipelines.
        text = text.replace(f"@{bot_username}", "").strip()

    # If inline-menu flow is waiting for org category, handle it first.
    if context.user_data.get("waiting_for_org_category"):
        # Clear waiting flag so only next message uses this branch.
        context.user_data.pop("waiting_for_org_category")
        # Inform user that organization search is running.
        await message.reply_text("🔍 Шукаю організації...", parse_mode=ParseMode.MARKDOWN)
        # Route user text to orchestrator with explicit show-orgs intent.
        reply = await pipeline_process_message(
            user.id,
            chat.id,
            chat.type,
            text,
            tg_message_id=message.message_id,
            forced_pipeline="show_orgs",
        )
        # Send search result and suppress URL previews for cleaner output.
        await message.reply_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        # Stop further processing for this message.
        return

    # Show typing indicator while main pipeline processes message.
    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    # Delegate standard text to orchestrator pipeline.
    reply = await pipeline_process_message(
        user.id, chat.id, chat.type, text, tg_message_id=message.message_id
    )
    # Send orchestrator-generated reply to user.
    await message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


# Global error handler for unhandled exceptions in update processing.
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Log exception stack trace.
    logger.error("Exception while handling update:", exc_info=context.error)
    # If update has a message context, send fallback error response to user.
    if isinstance(update, Update) and update.effective_message:
        # Notify user about runtime failure.
        await update.effective_message.reply_text(
            "⚠️ Сталася помилка. Спробуй ще раз пізніше."
        )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("style", cmd_style))
    
    for style in STYLES:
        app.add_handler(CommandHandler(f"style_{style}", cmd_style_shortcut))

    org_conv = ConversationHandler(
        # Entry point when user sends `/orgs` command.
        entry_points=[CommandHandler("orgs", cmd_orgs_start)],
        # States map for conversation transitions.
        states={
            # While waiting for category, accept plain text non-command messages.
            WAITING_FOR_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_orgs_receive_category)
            ],
        },
        # Allow `/cancel` command to terminate conversation.
        fallbacks=[CommandHandler("cancel", cmd_orgs_cancel)],
        # Use chat/user-based conversation keys (not message-based).
        per_message=False,
    )
    # Add conversation handler to application.
    app.add_handler(org_conv)

    # Register callback query handler for inline button actions.
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Register catch-all text handler for non-command messages.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register global error handler.
    app.add_error_handler(error_handler)

    # Log startup event.
    logger.info("Starting Hate-2-Action bot...")
    # Start long-polling loop for all update types.
    app.run_polling(allowed_updates=Update.ALL_TYPES)


# Run application only when file is executed as script.
if __name__ == "__main__":
    # Invoke bootstrap routine.
    main()
