"""
LLM utility module.

Purpose:
- Wrap OpenAI API calls used across pipelines for:
  - embeddings,
  - intent/style detection,
  - problem/solution extraction,
  - final natural-language response generation.

Design notes:
- This module is intentionally stateless beyond global client/model constants.
- Each function exposes one narrow model interaction and returns parsed Python data.
"""
import os
import json
from openai import OpenAI
from openai import OpenAIError
from dotenv import load_dotenv
load_dotenv()

_client: OpenAI | None = None
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-5.4-nano"

LANGUAGE_POLICY = {
    "uk": (
        "Відповідай виключно українською мовою. "
        "Не переходь на інші мови у звичайному тексті. "
        "Винятки: URL, офіційні назви організацій, технічні команди на кшталт /style_polite."
    ),
    "en": (
        "Reply exclusively in English. "
        "Do not switch to other languages in regular text. "
        "Exceptions: URLs, official organization names, technical commands like /style_polite."
    ),
}

STYLE_PROFILES = {
    "uk": {
        "polite": (
            "Чемний стиль: теплий, ввічливий і підтримувальний тон з емпатією, "
            "делікатними формулюваннями та спокійною подачею."
        ),
        "funny": (
            "Смішний стиль: легкий дотепний тон із доречним гумором, живою подачею "
            "та дружньою енергією без втрати практичності."
        ),
        "sarcastic": (
            "Саркастичний стиль: стримана іронія, колюча подача і тверезий погляд "
            "на проблему, але без образ і приниження."
        ),
        "normal": (
            "Нейтральний стиль: чіткий, збалансований і спокійний тон, фокус на "
            "структурі, ясності та конкретних кроках."
        ),
        "rude": (
            "Грубуватий стиль: прямий і жорсткий тон у форматі tough-love, мінімум "
            "дипломатії та максимум конкретики й дій."
        ),
    },
    "en": {
        "polite": (
            "Polite style: warm, courteous and supportive tone with empathy, "
            "delicate phrasing and calm delivery."
        ),
        "funny": (
            "Funny style: light witty tone with appropriate humor, lively delivery "
            "and friendly energy without losing practicality."
        ),
        "sarcastic": (
            "Sarcastic style: restrained irony, edgy delivery and sober outlook "
            "on the problem, but without insults or humiliation."
        ),
        "normal": (
            "Neutral style: clear, balanced and calm tone, focus on "
            "structure, clarity and concrete steps."
        ),
        "rude": (
            "Rude style: direct and tough tone in a tough-love format, minimal "
            "diplomacy and maximum specifics and action."
        ),
    },
}

RESPONSE_FORMAT = {
    "uk": """
Дотримуйся структури відповіді:
1. Валідація — коротко визнай емоції чи занепокоєння користувача.
2. Твереза порада — дай реалістичний погляд і конкретні кроки.
3. Підбадьорення — заверши мотивуючим закликом до дії.
Відповідь має бути стислою (3-5 речень).
""",
    "en": """
Follow this response structure:
1. Validation — briefly acknowledge the user's emotions or concerns.
2. Sober advice — give a realistic outlook and concrete steps.
3. Encouragement — end with a motivating call to action.
Keep the response concise (3-5 sentences).
""",
}


def detect_language(text: str) -> str:
    """Detect whether the message is in English or Ukrainian based on character analysis."""
    if not text:
        return "uk"
    # Strip commands, mentions, URLs
    import re
    cleaned = re.sub(r'(/\w+|@\w+|https?://\S+)', '', text).strip()
    if not cleaned:
        return "uk"
    cyrillic = sum(1 for c in cleaned if '\u0400' <= c <= '\u04ff')
    latin = sum(1 for c in cleaned if 'A' <= c <= 'Z' or 'a' <= c <= 'z')
    if latin > cyrillic:
        return "en"
    return "uk"
def _style_instruction(style: str, lang: str = "uk") -> str:
    normalized = style.strip().lower() if isinstance(style, str) else "normal"
    profiles = STYLE_PROFILES.get(lang, STYLE_PROFILES["uk"])
    resolved = normalized if normalized in profiles else "normal"
    description = profiles[resolved]
    policy = LANGUAGE_POLICY.get(lang, LANGUAGE_POLICY["uk"])
    if lang == "en":
        return (
            f"{policy}\n"
            f"Active style: {resolved}.\n"
            f"Style description: {description}"
        )
    return (
        f"{policy}\n"
        f"Активний стиль: {resolved}.\n"
        f"Опис стилю: {description}"
    )


def _get_client() -> OpenAI:
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    try:
        _client = OpenAI(api_key=api_key)
    except OpenAIError as exc:
        raise RuntimeError("Failed to initialize OpenAI client") from exc

    return _client


def get_embedding(text: str) -> list[float]:
    """Return a 1536-dim embedding for the given text."""
    response = _get_client().embeddings.create(model=EMBEDDING_MODEL, input=text[:8000])
    return response.data[0].embedding


def detect_pipeline(
    message: str,
    previous_message: str | None = None,
    previous_reply: str | None = None,
    previous_pipeline: str | None = None,
) -> str:
    previous_pipeline_name = (
        "problem_solution"
        if previous_pipeline == "process_message"
        else (previous_pipeline or "")
    )
    prompt = f"""Determine which Telegram bot pipeline should handle the new user message.

Return exactly ONE pipeline name:
- change_style
- show_orgs
- about_me
- problem_solution

What each pipeline does:

1. change_style
Choose if the user wants to change the tone or format of bot responses.
Intent examples: change style, write politely, write funny, less sarcasm, shorter, simpler, more formal, змінити стиль, писати ввічливо.

2. show_orgs
Choose if the user explicitly asks to find, show or suggest organizations, funds, initiatives, contacts, hotlines or places to turn to.
Also choose this if the bot's previous message asked for a topic/category for org search and the current message looks like such a topic.

3. about_me
Choose if the user asks who the bot is, what it can do, how to use it, what commands exist, its purpose or how it works.

4. problem_solution
Choose if the user describes a problem, outrage, conflict, injustice, stress or helplessness and wants to understand what to do next.
This is the main pipeline for complaints, emotional context, requests for practical steps, action plans or advice.

Routing rules:
- If there is an explicit request to change style, choose change_style even if there are other topics.
- If the user explicitly wants a list of organizations, contacts, funds, hotlines or places to turn to, choose show_orgs.
- If the user is mainly asking about the bot and its capabilities, choose about_me.
- If the user describes a problem and asks how to act, what to do, how to help or how to react, choose problem_solution.
- If in doubt, choose problem_solution.
- Ignore minor errors, transliteration, surzhyk and mixed languages if the intent is clear.

Previous conversation context:
Previous user message: "{previous_message or ''}"
Previous bot reply: "{previous_reply or ''}"
Previous pipeline: "{previous_pipeline_name}"

New user message:
"{message}"

Reply with only the pipeline name, no explanations."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=20,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    if result == "process_message":
        result = "problem_solution"
    valid = {"change_style", "show_orgs", "about_me", "problem_solution"}
    return result if result in valid else "problem_solution"


def extract_problems_and_solutions(message: str) -> dict:
    """Extract problems and solutions from a user complaint using LLM."""
    prompt = f"""Analyze this message and extract:
1. The core problems/issues the user is complaining about (1-3 specific problems)
2. General solution concepts that could address those problems (1-3 solutions)

Message: "{message}"

Respond in valid JSON with this exact structure:
{{
  "problems": [
    {{"name": "short problem name", "context": "brief context", "content": "detailed description"}}
  ],
  "solutions": [
    {{"name": "short solution name", "context": "brief context", "content": "detailed description"}}
  ]
}}"""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=600,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_reply(
    user_message: str,
    style: str,
    orgs: list[dict],
    projects: list[dict],
    history: list[dict] = None,
    lang: str = "uk",
) -> str:
    """Generate a styled reply with org/project recommendations."""
    style_instruction = _style_instruction(style, lang)
    unknown_org = "невідома організація" if lang == "uk" else "unknown organization"
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:3]
    )
    proj_list = "\n".join(
        f"- {p['name']} {'від' if lang == 'uk' else 'by'} {p.get('org_name', unknown_org)}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:3]
    )
    history_text = ""
    if history:
        user_label = "Користувач" if lang == "uk" else "User"
        bot_label = "Бот" if lang == "uk" else "Bot"
        header = "\nОстанній контекст розмови:\n" if lang == "uk" else "\nRecent conversation context:\n"
        history_text = header + "\n".join(
            f"{user_label}: {h['message_text']}\n{bot_label}: {h['reply_text']}" for h in history[-3:]
        )
    resp_format = RESPONSE_FORMAT.get(lang, RESPONSE_FORMAT["uk"])
    if lang == "en":
        system_prompt = f"""{style_instruction}
{resp_format}
You are the Hate-2-Action bot. Your task is to transform user frustration into concrete actions by recommending NGOs and projects.
Reply only in English.
Always mention 2-3 relevant organizations or projects from the list.
Format organization names as clickable Markdown links: [Name](url)"""
        no_orgs = "No specific organizations found."
        no_projs = "No specific projects found."
        user_prompt = f"""User message: "{user_message}"
{history_text}
Relevant organizations:
{org_list if org_list else no_orgs}

Relevant projects:
{proj_list if proj_list else no_projs}

Generate a response following the structure: validation → advice → encouragement."""
    else:
        system_prompt = f"""{style_instruction}
{resp_format}
Ти бот Hate-2-Action. Твоя задача — перетворювати обурення користувача на конкретні дії, рекомендуючи НГО та проєкти.
Відповідай тільки українською мовою.
Завжди згадай 2-3 релевантні організації або проєкти зі списку.
Назви організацій оформлюй як клікабельні Markdown-посилання: [Назва](url)"""
        user_prompt = f"""Повідомлення користувача: "{user_message}"
{history_text}
Релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

Релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Згенеруй відповідь за схемою: валідація → порада → підбадьорення."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=400,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_org_reply(query: str, orgs: list[dict], projects: list[dict], style: str, lang: str = "uk") -> str:
    """Generate a reply specifically for the Show Organizations pipeline."""
    style_instruction = _style_instruction(style, lang)
    na = "Н/Д" if lang == "uk" else "N/A"
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:5]
    )
    proj_list = "\n".join(
        f"- {p['name']} {'від' if lang == 'uk' else 'by'} {p.get('org_name', na)}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:5]
    )
    if lang == "en":
        no_orgs = "No specific organizations found."
        no_projs = "No specific projects found."
        user_prompt = f"""The user is looking for organizations on the topic: "{query}"

Here are relevant organizations:
{org_list if org_list else no_orgs}

And relevant projects:
{proj_list if proj_list else no_projs}

Provide a useful summary of the 2-4 most relevant organizations and how the user can support them.
Use Markdown links: [Name](url). Write concisely and practically."""
    else:
        user_prompt = f"""Користувач шукає організації за темою: "{query}"

Ось релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

І релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Зроби корисний підсумок для 2-4 найрелевантніших організацій і як користувач може їх підтримати.
Використовуй Markdown-посилання: [Назва](url). Пиши стисло та практично."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": style_instruction},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=400,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def detect_style_from_message(message: str) -> str | None:
    """Try to detect which style the user is requesting."""
    prompt = f"""Визнач, який стиль відповіді просить користувач.
Поверни ТІЛЬКИ одне слово: polite, funny, sarcastic, normal, rude, або unknown.

Варіанти стилів і сигнали:
- polite: чемний, ввічливий, теплий, підтримувальний тон.
  Ключові слова: будь ласка, дякую, ввічливо, тактовно, делікатно, з повагою, м'яко, коректно, politely, kind.
- funny: смішний, жартівливий, дотепний, легкий, playful тон.
  Ключові слова: жарт, дотеп, мем, смішно, кумедно, весело, з гумором, підкол, funny, humor.
- sarcastic: саркастичний, іронічний, сухий, колючий тон.
  Ключові слова: сарказм, іронія, колючо, їдко, гостро, без ілюзій, сухий гумор, sarcastic, snarky.
- normal: нейтральний, спокійний, збалансований, чіткий тон.
  Ключові слова: нейтрально, звичайно, стандартно, спокійно, без жартів, по суті, normal, neutral.
- rude: грубуватий, різкий, прямий, tough-love тон.
  Ключові слова: грубо, жорстко, прямо, без церемоній, різко, по факту, без прикрас, rude, blunt.

Правила:
- Якщо є явний запит на зміну стилю, обери найближчий стиль.
- Якщо стиль неочевидний, поверни unknown.
- Не додавай жодних пояснень.

Повідомлення: "{message}" """
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=10,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    return (
        result if result in set(STYLE_PROFILES["uk"].keys()) else None
    )


def enrich_query(query: str) -> str:
    """Expand a short query with keywords for better semantic search (max 800 chars)."""
    prompt = f"""Expand this query with relevant keywords and context for semantic search. Max 800 characters.
Query: "{query}"
Return only the enriched text."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=150,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()[:800]


def rewrite_reply_with_style(text: str, style: str, lang: str = "uk") -> str:
    """Apply style as a post-generation filter while preserving content."""
    if style == "normal":
        return text
    style_instruction = _style_instruction(style, lang)
    if lang == "en":
        system_prompt = (
            f"{style_instruction}\n"
            "Rewrite the text in the given tone. Do not invent new facts. "
            "Preserve Markdown links, organization/project names and practical steps. "
            "Return the final text in English only."
        )
        user_prompt = f"Original text:\n{text}\n\nReturn only the final rewritten text."
    else:
        system_prompt = (
            f"{style_instruction}\n"
            "Перепиши текст у заданому тоні. Не вигадуй нових фактів. "
            "Збережи Markdown-посилання, назви організацій/проєктів і практичні кроки. "
            "Фінальний текст поверни лише українською мовою."
        )
        user_prompt = f"Оригінальний текст:\n{text}\n\nПоверни тільки фінальний переписаний текст."
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
