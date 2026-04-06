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

from db import queries
from utils import llm

STYLES = ["polite", "funny", "sarcastic", "normal", "rude"]

STYLE_LABELS_UA = {
    "polite": "чемний",
    "funny": "смішний",
    "sarcastic": "саркастичний",
    "normal": "нейтральний",
    "rude": "грубуватий",
}


def _style_help_line(style: str) -> str:
    description = llm.STYLE_PROFILES.get(style, "")
    label = STYLE_LABELS_UA.get(style, style)
    return (
        f"• `/style_{style}` — *{label}* (`{style}`)\n"
        f"  Опис: {description}"
    )


def resolve_style(user_id: int, chat_id: int) -> str:
    user_style = queries.get_user_style(user_id)
    if user_style and user_style != "normal":
        return user_style
    chat_style = queries.get_chat_style(chat_id)
    if chat_style and chat_style != "normal":
        return chat_style
    return user_style or "normal"


async def pipeline_change_style(
    user_id: int,
    chat_id: int,
    chat_type: str,
    message: str = None,
    requested_style: str = None,
) -> str:
    style = requested_style
    if not style and message:
        style = llm.detect_style_from_message(message)
    if style and style in STYLES:
        queries.set_user_style(user_id, style)
        style_label = STYLE_LABELS_UA.get(style, style)
        style_description = llm.STYLE_PROFILES.get(style, "")
        style_options = ", ".join(
            f"{STYLE_LABELS_UA.get(s, s)} (`{s}`)" for s in STYLES
        )
        return (
            f"✅ Домовились! Надалі відповідатиму у стилі *{style_label}* (`{style}`).\n\n"
            f"Опис стилю: {style_description}\n"
            "\n"
            f"Доступні стилі: {style_options}"
        )
    return (
        "🎭 Обери стиль відповіді:\n\n"
        + "\n\n".join(_style_help_line(s) for s in STYLES)
        + "\n\nДоступні стилі: "
        + ", ".join(f"{STYLE_LABELS_UA.get(s, s)} (`{s}`)" for s in STYLES)
    )
