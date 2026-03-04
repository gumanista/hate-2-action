"""
Message orchestrator pipeline.

Purpose:
- Serve as the single entrypoint for incoming user text and dispatch it
  to the correct business pipeline.

Inputs:
- Identity/context: `user_id`, `chat_id`, `chat_type`, optional `tg_message_id`.
- Payload: raw `message_text` from Telegram.

Routing contract:
1. Bootstrap context by ensuring user and chat entities exist.
2. Detect intent label via LLM (`about_me`, `change_style`, `show_orgs`,
   fallback `process_message`).
3. Validate detected intent against `INTENT_PIPELINES`.
4. Route to handler:
   - `about_me` -> static help/about text.
   - `change_style` -> style preference pipeline.
   - `show_orgs` -> org lookup pipeline, with clarification guard for vague queries.
   - default -> problem/solution recommendation pipeline.
5. Persist each handled message pair with `pipeline_used` metadata.

Safety behavior:
- Any intent detection failure or unknown intent degrades gracefully to
  `process_message`.
- Top-level exceptions are logged and return a generic user-facing error.
"""

# Import logging to capture intent routing decisions and failures.
import logging
# Import regex utilities for lightweight text tokenization/cleanup.
import re

# Import DB query layer for persistence and retrieval operations.
from db import queries
# Import LLM utilities for intent and style detection.
from utils import llm

# Import pipeline that handles style change requests.
from .change_style import pipeline_change_style
# Import main problem-to-solution recommendation pipeline.
from .problem_solution import pipeline_problem_solution
# Import organization category lookup pipeline.
from .show_organizations import pipeline_show_orgs

# Create module-specific logger.
logger = logging.getLogger(__name__)

# Allowed intent labels that can be returned by intent detection.
INTENT_PIPELINES = {"change_style", "show_orgs", "about_me", "process_message"}

ABOUT_TEXT = (
    "👋 *Hate-2-Action Bot*\n\n"
    "Перетворюю твоє обурення на дію! 💪\n\n"
    "Напиши, що тебе бісить — корупція, клімат, нерівність чи будь-що інше — "
    "і я підкажу НГО та проєкти, які реально цим займаються.\n\n"
    "*Команди:*\n"
    "• /start — Почати\n"
    "• /style — Змінити стиль відповіді (polite/funny/sarcastic/normal/rude)\n"
    "• /orgs — Пошук організацій за категорією\n"
    "• /about — Що я вмію\n\n"
    "Просто напиши, що болить, а я допоможу спрямувати енергію в дію. 🔥"
)

START_TEXT = (
    "🚀 *Привіт! Я Hate-2-Action Bot!*\n\n"
    "Є щось у світі, що тебе дратує? Розкажи мені.\n"
    "Я вислухаю і підкажу людей та ініціативи, які вже працюють над "
    "розвʼязанням проблеми.\n\n"
    "Просто опиши проблему, і я знайду релевантні НГО та проєкти.\n\n"
    "Або скористайся /orgs для пошуку організацій, /style для зміни тону, "
    "або /about щоб дізнатись більше."
)


def pipeline_about_me() -> str:
    return ABOUT_TEXT


def pipeline_start() -> str:
    return START_TEXT


# Detect pipeline intent safely and normalize to a known value.
def _detect_pipeline_name(message_text: str) -> str:
    """Safely detect the intent pipeline. Fall back to process_message."""
    try:
        # TODO - to fix the prompt for detecting messages
        # Ask LLM to classify incoming message into one of pipeline names.
        detected = llm.detect_pipeline(message_text)
    except Exception as e:
        # Log detection failure and continue with default pipeline.
        logger.warning(
            f"Pipeline detection failed, defaulting to process_message: {e}"
        )
        # Default to generic processing when detection fails.
        return "process_message"

    # Guard against unexpected non-string responses.
    if not isinstance(detected, str):
        return "process_message"
    # Normalize intent token to reduce casing/spacing issues.
    detected = detected.strip().lower()
    # Return only known intents; unknown labels fall back to generic processing.
    return detected if detected in INTENT_PIPELINES else "process_message"


# TODO: to get rid of the tokens, make the llm extend the message for the similarity search
# Heuristic to decide whether `/orgs`-like request lacks concrete category details.
def _needs_org_category_clarification(message_text: str) -> bool:
    """Detect if user asked to find orgs but did not provide a clear category."""
    # Remove punctuation and lower-case text for simpler token checks.
    cleaned = re.sub(r"[^\w\s]", " ", message_text.lower())
    # Split by whitespace and drop empty tokens.
    tokens = [t for t in cleaned.split() if t]
    # Very short queries are too ambiguous and need clarification.
    if len(tokens) <= 2:
        # Ask user for explicit topic/category.
        return True

    # Generic words that indicate request intent but not category specificity.
    generic = {
        # English command-like tokens.
        "show",
        "find",
        "org",
        "orgs",
        "organization",
        "organizations",
        "ngo",
        "ngos",
        # Ukrainian command-like tokens.
        "знайди",
        "покажи",
        "організація",
        "організації",
        "організацію",
        "нго",
    }
    # Clarification is needed when every token is generic (no topic words present).
    return all(token in generic for token in tokens)


# TODO: factory pattern for pipelines (pipeline class); ADK agent development kit
# Main entrypoint called for ordinary incoming user messages.
async def pipeline_process_message(
    # Telegram user id.
    user_id: int,
    # Telegram chat id.
    chat_id: int,
    # Telegram chat type.
    chat_type: str,
    # Raw incoming user message text.
    message_text: str,
    # Optional Telegram message id.
    tg_message_id: int = None,
) -> str:
    """
    Main message entrypoint:
    - classify intent via LLM
    - execute the appropriate pipeline
    """
    try:
        # Ensure user exists before any downstream storage operations.
        queries.get_or_create_user(user_id)
        # Ensure chat exists before any downstream storage operations.
        queries.get_or_create_chat(chat_id, chat_type)

        # Determine which pipeline should handle this message.
        pipeline_name = _detect_pipeline_name(message_text)
        # Record routing decision in logs.
        logger.info(f"Detected pipeline: {pipeline_name} for user {user_id}")

        # Route static about requests.
        if pipeline_name == "about_me":
            # Build static about reply.
            reply = pipeline_about_me()
            # Save request/response pair with pipeline metadata.
            queries.save_message(
                # Chat context id.
                chat_id,
                # User context id.
                user_id,
                # Original user message.
                message_text,
                # Generated reply text.
                reply,
                # Optional Telegram message identifier.
                tg_message_id=tg_message_id,
                # Mark which pipeline produced the output.
                pipeline_used="about_me",
            )
            # Return response immediately.
            return reply

        # Route style-change requests.
        if pipeline_name == "change_style":
            # Try to extract explicit style target from message text.
            requested_style = llm.detect_style_from_message(message_text)
            # Delegate to dedicated style-change pipeline.
            reply = await pipeline_change_style(
                # Forward user id.
                user_id,
                # Forward chat id.
                chat_id,
                # Forward chat type.
                chat_type,
                # Pass original message for fallback style detection.
                message=message_text,
                # Pass already detected requested style.
                requested_style=requested_style,
            )
            # Persist response and routing metadata.
            queries.save_message(
                # Chat context id.
                chat_id,
                # User context id.
                user_id,
                # Original user message.
                message_text,
                # Generated reply text.
                reply,
                # Optional Telegram message identifier.
                tg_message_id=tg_message_id,
                # Pipeline marker for analytics/debugging.
                pipeline_used="change_style",
            )
            # Return response immediately.
            return reply

        # Route organization listing requests.
        if pipeline_name == "show_orgs":
            # If category is unclear, request clarification instead of fuzzy lookup.
            if _needs_org_category_clarification(message_text):
                # Prepare clarification prompt with concrete examples.
                reply = (
                    "🏢 Організації якої категорії тебе цікавлять?\n\n"
                    "Напиши тему, наприклад: клімат, корупція, освіта, здоровʼя."
                )
                # Save clarification response as normal pipeline output.
                queries.save_message(
                    # Chat context id.
                    chat_id,
                    # User context id.
                    user_id,
                    # Original user message.
                    message_text,
                    # Clarification question reply.
                    reply,
                    # Optional Telegram message identifier.
                    tg_message_id=tg_message_id,
                    # Pipeline marker for analytics/debugging.
                    pipeline_used="show_orgs",
                )
                # Return clarification prompt.
                return reply

            # Delegate to dedicated organizations pipeline when category is clear.
            return await pipeline_show_orgs(
                # Forward user id.
                user_id,
                # Forward chat id.
                chat_id,
                # Forward chat type.
                chat_type,
                # Forward user category query.
                message_text,
                # Forward Telegram message id.
                tg_message_id=tg_message_id,
            )

        # Default route: run main problem-to-solution recommendation pipeline.
        return await pipeline_problem_solution(
            # Forward user id.
            user_id,
            # Forward chat id.
            chat_id,
            # Forward chat type.
            chat_type,
            # Forward user message.
            message_text,
            # Forward Telegram message id.
            tg_message_id=tg_message_id,
        )

    except Exception as e:
        # Log full stack trace for unexpected orchestration errors.
        logger.error(f"process_message pipeline error: {e}", exc_info=True)
        # Return safe fallback error text for end users.
        return "⚠️ Під час обробки повідомлення сталася помилка. Спробуй ще раз."
