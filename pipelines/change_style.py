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

STYLE_LABELS_EN = {
    "polite": "polite",
    "funny": "funny",
    "sarcastic": "sarcastic",
    "normal": "neutral",
    "rude": "rude",
}

STYLE_LABELS = {"uk": STYLE_LABELS_UA, "en": STYLE_LABELS_EN}


def _style_help_line(style: str, lang: str = "uk") -> str:
    profiles = llm.STYLE_PROFILES.get(lang, llm.STYLE_PROFILES["uk"])
    description = profiles.get(style, "")
    labels = STYLE_LABELS.get(lang, STYLE_LABELS_UA)
    label = labels.get(style, style)
    desc_word = "Description" if lang == "en" else "Опис"
    return (
        f"• `/style_{style}` — *{label}* (`{style}`)\n"
        f"  {desc_word}: {description}"
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
    lang: str = "uk",
) -> str:
    style = requested_style
    if not style and message:
        style = llm.detect_style_from_message(message)
    labels = STYLE_LABELS.get(lang, STYLE_LABELS_UA)
    profiles = llm.STYLE_PROFILES.get(lang, llm.STYLE_PROFILES["uk"])
    if style and style in STYLES:
        queries.set_user_style(user_id, style)
        style_label = labels.get(style, style)
        style_description = profiles.get(style, "")
        style_options = ", ".join(
            f"{labels.get(s, s)} (`{s}`)" for s in STYLES
        )
        if lang == "en":
            return (
                f"✅ Done! From now on I'll reply in *{style_label}* (`{style}`) style.\n\n"
                f"Style description: {style_description}\n"
                "\n"
                f"Available styles: {style_options}"
            )
        return (
            f"✅ Домовились! Надалі відповідатиму у стилі *{style_label}* (`{style}`).\n\n"
            f"Опис стилю: {style_description}\n"
            "\n"
            f"Доступні стилі: {style_options}"
        )
    if lang == "en":
        return (
            "🎭 Choose a response style:\n\n"
            + "\n\n".join(_style_help_line(s, lang) for s in STYLES)
            + "\n\nAvailable styles: "
            + ", ".join(f"{labels.get(s, s)} (`{s}`)" for s in STYLES)
        )
    return (
        "🎭 Обери стиль відповіді:\n\n"
        + "\n\n".join(_style_help_line(s, lang) for s in STYLES)
        + "\n\nДоступні стилі: "
        + ", ".join(f"{labels.get(s, s)} (`{s}`)" for s in STYLES)
    )
