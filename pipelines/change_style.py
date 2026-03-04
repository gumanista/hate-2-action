"""
Change style pipeline.

Purpose:
- Centralize tone/style selection and persistence for user replies.

Inputs:
- `user_id`, `chat_id`, `chat_type` identify context for preference storage.
- `requested_style` may come from a parsed command (for example `/style_funny`).
- `message` is used as fallback for style detection when explicit style is absent.

Core logic:
1. Ensure user/chat records exist so style updates have a valid target.
2. Resolve candidate style from explicit request first, then LLM detection.
3. Validate style against supported enum (`STYLES`) to prevent invalid DB values.
4. Persist user-level style preference when valid.
5. Return either:
   - a confirmation message with selected style and available options, or
   - a style-picker help message when style is missing/invalid.

Style precedence model:
- Runtime response style is resolved elsewhere through `resolve_style(...)`:
  user non-default style -> chat non-default style -> user/default `normal`.
"""

# Import database query helpers for reading and writing style preferences.
from db import queries
# Import LLM helpers used to detect a style from free-form message text.
from utils import llm

# Define the list of supported internal style identifiers.
STYLES = ["polite", "funny", "sarcastic", "normal", "rude"]

# Map internal style identifiers to user-facing Ukrainian labels.
STYLE_LABELS_UA = {
    # Human-readable label for the polite style.
    "polite": "чемний",
    # Human-readable label for the funny style.
    "funny": "смішний",
    # Human-readable label for the sarcastic style.
    "sarcastic": "саркастичний",
    # Human-readable label for the neutral/default style.
    "normal": "нейтральний",
    # Human-readable label for the rough/rude style.
    "rude": "грубуватий",
}


# Resolve active style with priority: explicit user style, then chat style, then normal.
def resolve_style(user_id: int, chat_id: int) -> str:
    """Resolve style: user preference -> chat preference -> default normal."""
    # Load stored style preference for the current user.
    user_style = queries.get_user_style(user_id)
    # If user has a non-default style, use it immediately.
    if user_style and user_style != "normal":
        # Return strongest preference level (user-specific non-default style).
        return user_style
    # Otherwise load style preference configured at chat level.
    chat_style = queries.get_chat_style(chat_id)
    # If chat has a non-default style, use it as fallback.
    if chat_style and chat_style != "normal":
        # Return chat-level style when no user-level override is set.
        return chat_style
    # If user style exists (including "normal"), use it; else default to "normal".
    return user_style or "normal"


# Main async pipeline that sets style from command or detected intent text.
async def pipeline_change_style(
    # Telegram user identifier.
    user_id: int,
    # Telegram chat identifier.
    chat_id: int,
    # Telegram chat type (private/group/etc).
    chat_type: str,
    # Optional original text message used for style detection.
    message: str = None,
    # Optional explicit style already parsed from command/intention.
    requested_style: str = None,
) -> str:
    # Ensure the user row exists before attempting updates.
    queries.get_or_create_user(user_id)
    # Ensure the chat row exists before reading or writing chat-related data.
    queries.get_or_create_chat(chat_id, chat_type)

    # Start with explicitly provided style if caller already detected one.
    style = requested_style
    # If no explicit style was provided but message text exists, infer style from text.
    if not style and message:
        # Ask the LLM to detect one of supported style keywords from the message.
        style = llm.detect_style_from_message(message)

    # Continue with save/confirmation branch only for supported style values.
    if style and style in STYLES:
        # Persist selected style as user-level preference.
        queries.set_user_style(user_id, style)
        # Resolve localized style label for response text.
        style_label = STYLE_LABELS_UA.get(style, style)
        # Build display list of all available styles with localized + internal names.
        style_options = ", ".join(
            # Convert each style to `localized (internal)` format.
            f"{STYLE_LABELS_UA.get(s, s)} (`{s}`)" for s in STYLES
        )
        # Return confirmation message plus reminder of all available styles.
        return (
            # First paragraph confirms selected style.
            f"✅ Домовились! Надалі відповідатиму у стилі *{style_label}* (`{style}`).\n\n"
            # Second paragraph lists style options for future changes.
            f"Доступні стилі: {style_options}"
        )

    # Fallback response when style was missing or invalid: show how to choose styles.
    return (
        # Header prompting user to choose a response style.
        "🎭 Обери стиль відповіді:\n\n"
        # Command-style list (`/style_polite`, etc.) generated from supported styles.
        + "\n".join(f"• /style_{s} — {STYLE_LABELS_UA.get(s, s)}" for s in STYLES)
        # Footer with the same style list in `localized (internal)` format.
        + "\n\nДоступні стилі: "
        # Append localized/internal style options in one comma-separated line.
        + ", ".join(f"{STYLE_LABELS_UA.get(s, s)} (`{s}`)" for s in STYLES)
    )
