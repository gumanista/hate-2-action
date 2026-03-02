"""
Shared constants and helpers for all pipeline modules.
"""

from db import queries

STYLES = ["polite", "funny", "sarcastic", "normal", "rude"]

STYLE_LABELS_UA = {
    "polite": "чемний",
    "funny": "смішний",
    "sarcastic": "саркастичний",
    "normal": "нейтральний",
    "rude": "грубуватий",
}

INTENT_PIPELINES = {"change_style", "show_orgs", "about_me", "process_message"}
ORG_PROJECT_LINK_THRESHOLD = 0.3
PROBLEM_SOLUTION_LINK_THRESHOLD = 0.35

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


def resolve_style(user_id: int, chat_id: int) -> str:
    """Resolve style: user preference -> chat preference -> default normal."""
    user_style = queries.get_user_style(user_id)
    if user_style and user_style != "normal":
        return user_style
    chat_style = queries.get_chat_style(chat_id)
    if chat_style and chat_style != "normal":
        return chat_style
    return user_style or "normal"
