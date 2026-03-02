"""
Change style pipeline.

Flow:
1. Detect requested style from explicit command or message intent.
2. Persist user preference.
3. Return confirmation or available style options.
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


def resolve_style(user_id: int, chat_id: int) -> str:
    """Resolve style: user preference -> chat preference -> default normal."""
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
    queries.get_or_create_user(user_id)
    queries.get_or_create_chat(chat_id, chat_type)

    style = requested_style
    if not style and message:
        style = llm.detect_style_from_message(message)

    if style and style in STYLES:
        queries.set_user_style(user_id, style)
        style_label = STYLE_LABELS_UA.get(style, style)
        style_options = ", ".join(
            f"{STYLE_LABELS_UA.get(s, s)} (`{s}`)" for s in STYLES
        )
        return (
            f"✅ Домовились! Надалі відповідатиму у стилі *{style_label}* (`{style}`).\n\n"
            f"Доступні стилі: {style_options}"
        )

    return (
        "🎭 Обери стиль відповіді:\n\n"
        + "\n".join(f"• /style_{s} — {STYLE_LABELS_UA.get(s, s)}" for s in STYLES)
        + "\n\nДоступні стилі: "
        + ", ".join(f"{STYLE_LABELS_UA.get(s, s)} (`{s}`)" for s in STYLES)
    )
