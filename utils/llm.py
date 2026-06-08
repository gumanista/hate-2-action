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
load_dotenv(".env.local", override=True)

try:
    from google import genai as google_genai
    from google.genai import types as google_genai_types
except ImportError:
    google_genai = None
    google_genai_types = None

_client: OpenAI | None = None
_gemini_client = None
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-5.4-nano"


def _is_gemini_model(model: str) -> bool:
    return isinstance(model, str) and model.lower().startswith("gemini")

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
            "Чемний стиль: теплий, м'який і підтримувальний тон з емпатією, "
            "делікатними формулюваннями та спокійною подачею. "
            "На початку коротко поясни, чому скарга користувача справедлива "
            "(в чому суть проблеми), і допоможи практично. "
            "Тримай відповідь стислою (3-4 речення) — без води."
        ),
        "funny": (
            "Смішний стиль: жартівливий, грайливий тон зі справжніми жартами, "
            "грою слів, дотепними порівняннями та легкою самоіронією — гумор має "
            "бути відчутним, а не лише натяком на дружній тон. "
            "Починай з жарту або дотепного спостереження про ситуацію. "
            "ВАЖЛИВО: НЕ припускай, що користувач 'злиться', 'тригериться', "
            "'його вивертає' чи 'накрило'. Людина може просто коментувати ситуацію "
            "без емоційного навантаження. Уникай слів 'злість', 'обурення' та "
            "фраз типу 'тебе тригернуло', 'тебе вивертає', 'твоя злість'. "
            "Жартуй з ситуації, абсурду чи з самого себе — не з користувача. "
            "Не ображай, не повчай, не натискай. "
            "Тримай відповідь дуже короткою (2-3 речення), щоб жарт спрацював."
        ),
        "sarcastic": (
            "Саркастичний стиль: гострий, сухий і влучний сарказм у дусі "
            "Леся Подерв'янського — висміюй ситуацію, лицемірство, абсурд чи "
            "систему, а не самого користувача. "
            "Сарказм має бути різким, конкретним і коротким — не м'яким. "
            "Можеш ставити риторичні питання користувачеві ('а ти що думав?', "
            "'хто б міг подумати?'). Допомагати — на власний розсуд: "
            "іноді доречно дати конкретний крок, іноді — лише підсвітити абсурд. "
            "НЕ коментуй емоції користувача ('ти злий', 'ти нервуєш', "
            "'тебе обурює') — говори про ситуацію, а не про його стан. "
            "Якщо користувач у своєму повідомленні вживає нецензурну лексику, "
            "можеш у міру відповідати в тому ж регістрі (без переходу на "
            "особисті образи проти користувача). "
            "Без моралізаторства й політичних повчань. "
            "Тримай відповідь дуже короткою (2-3 речення) — сарказм має бути швидким."
        ),
        "normal": (
            "Нейтральний стиль: сухий, чіткий, збалансований тон без емоцій. "
            "Коротко окресли проблему й перерахуй можливі рішення/кроки. "
            "Без валідації емоцій, без підбадьорень — тільки суть. "
            "Тримай відповідь стислою (3-4 речення)."
        ),
        "rude": (
            "Грубуватий стиль: прямий, різкий і жорсткий тон у форматі tough-love, "
            "мінімум дипломатії та максимум конкретики й дій. "
            "Можна бути грубуватим у формулюваннях, АЛЕ ніколи не ображай "
            "самого користувача — критикуй ситуацію, систему, бездіяльність. "
            "Тримайся теми повідомлення — без зайвих відступів. "
            "Тримай відповідь короткою (3-4 речення)."
        ),
    },
    "en": {
        "polite": (
            "Polite style: warm, soft and supportive tone with empathy, "
            "delicate phrasing and calm delivery. "
            "Start by briefly explaining why the user's concern is valid "
            "(what the actual issue is) and help practically. "
            "Keep the response concise (3-4 sentences) — no fluff."
        ),
        "funny": (
            "Funny style: playful, jokey tone with real jokes, wordplay, witty "
            "comparisons and light self-irony — humor must be tangible, not just "
            "a hint of friendly tone. "
            "Open with a joke, pun or witty observation about the situation. "
            "IMPORTANT: do NOT assume the user is 'angry', 'triggered', 'fuming' "
            "or 'losing it'. They may simply be commenting on the situation "
            "without heavy emotion. Avoid words like 'anger', 'rage' and phrases "
            "like 'you're triggered', 'this is eating you up', 'your anger'. "
            "Joke about the situation, the absurdity, or yourself — not the user. "
            "Don't insult, lecture or pressure. "
            "Keep the response very short (2-3 sentences) so the joke lands."
        ),
        "sarcastic": (
            "Sarcastic style: sharp, dry, on-point sarcasm — mock the situation, "
            "hypocrisy, absurdity or the system, not the user themselves. "
            "Sarcasm should be cutting, specific and short — not soft. "
            "Rhetorical questions to the user are welcome ('what did you expect?'). "
            "Helping is optional — sometimes a concrete step lands, sometimes "
            "just exposing the absurd is enough. "
            "Do NOT comment on the user's emotions ('you're angry', 'you're upset', "
            "'this is frustrating you') — talk about the situation, not their state. "
            "If the user uses profanity in their own message, you may match the "
            "register moderately (without crossing into personal insults against "
            "the user). "
            "No moralizing or political lecturing. "
            "Keep the response very short (2-3 sentences) — sarcasm should be quick."
        ),
        "normal": (
            "Neutral style: dry, clear, balanced tone with no emotions. "
            "Briefly state the problem and list possible solutions/steps. "
            "No emotional validation, no encouragement — just the substance. "
            "Keep the response concise (3-4 sentences)."
        ),
        "rude": (
            "Rude style: direct, sharp and tough tone in a tough-love format, "
            "minimal diplomacy and maximum specifics and action. "
            "You can be blunt in phrasing, BUT never insult the user themselves — "
            "criticize the situation, the system, the inaction. "
            "Stay on the topic of the message — no detours. "
            "Keep the response short (3-4 sentences)."
        ),
    },
}

RESPONSE_FORMAT = {
    "uk": """
Загальні правила відповіді:
- Дай коротку реалістичну пораду й один-два конкретні кроки.
- Завершуй практичним закликом, а не довгим підбадьоренням.
- Структуру (валідація → порада → заклик) застосовуй лише в стилях polite і funny —
  для sarcastic, rude і normal валідацію та підбадьорення можна повністю прибрати
  й одразу переходити до суті.
- Відповідь має бути стислою — максимум 3-4 речення (для funny/sarcastic — 2-3).
- НЕ припускай емоційний стан користувача ('ти злий', 'ти нервуєш', 'тебе обурює') —
  говори про ситуацію, а не про його почуття.
- НЕ припускай географію користувача — не називай конкретних міст, районів чи
  країн, якщо користувач сам їх не назвав.
- Згадуй ЛИШЕ ті організації/проєкти, що прямо стосуються теми повідомлення.
  Краще згадати одну релевантну організацію, ніж три не за темою.
""",
    "en": """
General response rules:
- Give brief, realistic advice and one or two concrete steps.
- End with a practical call to action, not a long pep talk.
- Use the (validation → advice → call) structure only for polite and funny styles —
  for sarcastic, rude and normal styles you may drop validation and encouragement
  entirely and go straight to the substance.
- Keep responses concise — max 3-4 sentences (for funny/sarcastic — 2-3).
- Do NOT assume the user's emotional state ('you're angry', 'you're upset',
  'this is frustrating you') — talk about the situation, not their feelings.
- Do NOT assume the user's location — don't name specific cities, districts or
  countries unless the user has named them themselves.
- Mention ONLY organizations/projects directly relevant to the message topic.
  One on-topic org beats three off-topic ones.
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


def _get_gemini_client():
    """Return a singleton google-genai Client. Reads GEMINI_API_KEY (or GOOGLE_API_KEY)."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if google_genai is None:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        )
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")
    _gemini_client = google_genai.Client(api_key=api_key)
    return _gemini_client


def _gemini_chat(
    messages: list[dict],
    *,
    max_output_tokens: int,
    json_mode: bool = False,
) -> str:
    """Translate OpenAI-style messages to a Gemini call and return assistant text.

    System messages are merged into `system_instruction`; the rest are
    concatenated into a single user `contents` string. Good enough for the
    short, mostly single-turn prompts in this module.
    """
    system_parts: list[str] = []
    user_parts: list[str] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)
    config_kwargs: dict = {"max_output_tokens": max_output_tokens}
    if system_parts:
        config_kwargs["system_instruction"] = "\n\n".join(system_parts)
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    config = google_genai_types.GenerateContentConfig(**config_kwargs)
    response = _get_gemini_client().models.generate_content(
        model=CHAT_MODEL,
        contents="\n\n".join(user_parts) if user_parts else " ",
        config=config,
    )
    return (response.text or "").strip()


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
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_detect_pipeline(message, previous_message, previous_reply, previous_pipeline)
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
    )
    result = response.choices[0].message.content.strip().lower()
    if result == "process_message":
        result = "problem_solution"
    valid = {"change_style", "show_orgs", "about_me", "problem_solution"}
    return result if result in valid else "problem_solution"


def extract_problems_and_solutions(message: str) -> dict:
    """Extract problems and solutions from a user complaint using LLM."""
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_extract_problems_and_solutions(message)
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
        max_completion_tokens=1500,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"problems": [], "solutions": []}


def generate_reply(
    user_message: str,
    style: str,
    orgs: list[dict],
    projects: list[dict],
    history: list[dict] = None,
    lang: str = "uk",
) -> str:
    """Generate a styled reply with org/project recommendations."""
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_generate_reply(user_message, style, orgs, projects, history, lang)
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
Mention 1-3 organizations or projects from the list, but ONLY those that genuinely fit the topic of the user's message. If none of the listed orgs fit the topic, mention zero — do not pad the answer with off-topic links.
Format organization names as clickable Markdown links: [Name](url).
Keep it short and on-topic; obey the style profile's length limit."""
        no_orgs = "No specific organizations found."
        no_projs = "No specific projects found."
        user_prompt = f"""User message: "{user_message}"
{history_text}
Relevant organizations:
{org_list if org_list else no_orgs}

Relevant projects:
{proj_list if proj_list else no_projs}

Generate a short, on-topic response in the active style. Skip orgs that don't match the topic of this specific message."""
    else:
        system_prompt = f"""{style_instruction}
{resp_format}
Ти бот Hate-2-Action. Твоя задача — перетворювати обурення користувача на конкретні дії, рекомендуючи НГО та проєкти.
Відповідай тільки українською мовою.
Згадуй 1-3 організації або проєкти зі списку, але ЛИШЕ ті, що реально відповідають темі повідомлення користувача. Якщо жодна зі списку не підходить — не згадуй жодної, краще коротка відповідь без лінків, ніж довга з не-за-темою посиланнями.
Назви організацій оформлюй як клікабельні Markdown-посилання: [Назва](url).
Тримай відповідь короткою і по темі; дотримуйся обмеження довжини зі стилю."""
        user_prompt = f"""Повідомлення користувача: "{user_message}"
{history_text}
Релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

Релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Згенеруй коротку відповідь по темі в активному стилі. Не згадуй організації, що не стосуються теми саме цього повідомлення."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=400,
    )
    return response.choices[0].message.content.strip()


def generate_org_reply(query: str, orgs: list[dict], projects: list[dict], style: str, lang: str = "uk") -> str:
    """Generate a reply specifically for the Show Organizations pipeline."""
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_generate_org_reply(query, orgs, projects, style, lang)
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
    )
    return response.choices[0].message.content.strip()


def detect_style_from_message(message: str) -> str | None:
    """Try to detect which style the user is requesting."""
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_detect_style_from_message(message)
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
    )
    result = response.choices[0].message.content.strip().lower()
    return (
        result if result in set(STYLE_PROFILES["uk"].keys()) else None
    )


def enrich_query(query: str) -> str:
    """Expand a short query with keywords for better semantic search (max 800 chars)."""
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_enrich_query(query)
    prompt = f"""Expand this query with relevant keywords and context for semantic search. Max 800 characters.
Query: "{query}"
Return only the enriched text."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=150,
    )
    return response.choices[0].message.content.strip()[:800]


def rewrite_reply_with_style(text: str, style: str, lang: str = "uk", original_message: str | None = None) -> str:
    """Apply style as a post-generation filter while preserving content."""
    if _is_gemini_model(CHAT_MODEL):
        return _gemini_rewrite_reply_with_style(text, style, lang, original_message)
    style_instruction = _style_instruction(style, lang)
    style_specific_en = ""
    style_specific_uk = ""
    if style == "funny":
        style_specific_en = (
            "Open the rewritten text with a joke, pun or witty observation about "
            "the situation — not with emotional validation. "
            "If the original starts with phrases like 'I see you're triggered', "
            "'this is eating you up', 'your anger is valid', REPLACE that opening "
            "with humor about the situation, not about the user's emotions. "
            "Don't tell the user how they feel. "
            "Aim for actual humor (wordplay, absurd comparison, self-irony), not "
            "just a friendly tone. "
            "Cut hard — final text should be 2-3 sentences max."
        )
        style_specific_uk = (
            "Починай переписаний текст з жарту або дотепного спостереження про "
            "ситуацію — не з емоційної валідації. "
            "Якщо оригінал починається фразами типу 'бачу, тебе тригернуло', "
            "'тебе вивертає', 'твоя злість зрозуміла', ЗАМІНИ цей вступ на гумор "
            "про ситуацію, а не про емоції користувача. "
            "Не кажи користувачу, що він відчуває. "
            "Цілься у справжній гумор (гра слів, абсурдне порівняння, самоіронія), "
            "а не просто дружній тон. Підсумок у кінці не має згадувати 'злість' "
            "чи 'обурення' користувача. "
            "Скорочуй сильно — фінальний текст 2-3 речення максимум."
        )
    elif style == "sarcastic":
        style_specific_en = (
            "Make sarcasm sharper and shorter — cut soft, hedging phrases and any "
            "long pep-talk endings. "
            "Mock the situation/system/absurdity, not the user. "
            "Do not narrate the user's emotions ('you're angry', 'you're upset'). "
            "A rhetorical question to the user is welcome. "
            "Helping is optional — if no listed org genuinely fits the topic, "
            "drop the org list entirely rather than padding. "
            "If the original user message contains profanity, you may match the "
            "register moderately. "
            "Final text: 2-3 sentences max."
        )
        style_specific_uk = (
            "Зроби сарказм гострішим і коротшим — приберай м'які, обережні "
            "формулювання та довгі мотиваційні кінцівки. "
            "Висміюй ситуацію/систему/абсурд, не самого користувача. "
            "Не коментуй емоції користувача ('ти злий', 'ти нервуєш', 'тебе обурює'). "
            "Доречне риторичне питання до користувача. "
            "Допомагати — необов'язково: якщо жодна організація зі списку не "
            "стосується теми, краще прибери блок з організаціями повністю, ніж "
            "вставляй не за темою. "
            "Якщо в оригінальному повідомленні користувача є нецензурна лексика, "
            "можна помірно вживати її і у відповіді (без особистих образ). "
            "Фінальний текст: 2-3 речення максимум."
        )
    elif style == "polite":
        style_specific_en = (
            "Soften the tone further — warm and supportive, not preachy. "
            "Start by briefly explaining why the user's concern is valid (the "
            "actual issue), then help with one practical step. "
            "Cut filler — final text 3-4 sentences."
        )
        style_specific_uk = (
            "Зроби тон ще м'якішим — теплий і підтримувальний, без повчань. "
            "На початку коротко поясни, чому скарга користувача справедлива (в чому "
            "суть проблеми), а потім допоможи одним практичним кроком. "
            "Прибери воду — фінальний текст 3-4 речення."
        )
    elif style == "rude":
        style_specific_en = (
            "Sharper, blunter, more direct — but never insult the user. "
            "Stay strictly on the topic of the user's message. "
            "Do NOT name specific cities, regions or countries that the user did "
            "not mention themselves — you don't know where the user is. "
            "Final text: 3-4 sentences."
        )
        style_specific_uk = (
            "Різкіше, грубіше, прямолінійніше — але без образ користувача. "
            "Тримайся строго теми повідомлення користувача. "
            "НЕ називай конкретних міст, областей чи країн, яких користувач сам не "
            "згадував — ти не знаєш, звідки користувач. "
            "Фінальний текст: 3-4 речення."
        )
    elif style == "normal":
        style_specific_en = (
            "Make it dry and matter-of-fact: state the problem briefly, list "
            "concrete options/steps, stop. No emotional validation, no pep talk. "
            "Final text: 3-4 sentences."
        )
        style_specific_uk = (
            "Сухо і по суті: коротко окресли проблему, перерахуй конкретні "
            "варіанти/кроки, і все. Без валідації емоцій, без підбадьорень. "
            "Фінальний текст: 3-4 речення."
        )
    if lang == "en":
        system_prompt = (
            f"{style_instruction}\n"
            "Rewrite the text in the given tone. Do not invent new facts. "
            "Preserve Markdown links, organization/project names and practical steps. "
            f"{style_specific_en} "
            "Return the final text in English only."
        )
        original_block = f"\n\nUser's original message (for context, do NOT rewrite it):\n{original_message}\n" if original_message else ""
        user_prompt = f"Original text:\n{text}{original_block}\n\nReturn only the final rewritten text."
    else:
        system_prompt = (
            f"{style_instruction}\n"
            "Перепиши текст у заданому тоні. Не вигадуй нових фактів. "
            "Збережи Markdown-посилання, назви організацій/проєктів і практичні кроки. "
            f"{style_specific_uk} "
            "Фінальний текст поверни лише українською мовою."
        )
        original_block = f"\n\nОригінальне повідомлення користувача (для контексту, не переписуй його):\n{original_message}\n" if original_message else ""
        user_prompt = f"Оригінальний текст:\n{text}{original_block}\n\nПоверни тільки фінальний переписаний текст."
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=500,
    )
    return response.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════════
# Google Gemini implementations
# Used when CHAT_MODEL is a Gemini model (see _is_gemini_model).
# Each function below mirrors its OpenAI sibling above; routing happens via
# the early-return guards at the top of each public function.
# ══════════════════════════════════════════════════════════════════════════


def _gemini_detect_pipeline(
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
    result = _gemini_chat(
        [{"role": "user", "content": prompt}],
        max_output_tokens=20,
    ).strip().lower()
    if result == "process_message":
        result = "problem_solution"
    valid = {"change_style", "show_orgs", "about_me", "problem_solution"}
    return result if result in valid else "problem_solution"


def _gemini_extract_problems_and_solutions(message: str) -> dict:
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
    content = _gemini_chat(
        [{"role": "user", "content": prompt}],
        max_output_tokens=1500,
        json_mode=True,
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"problems": [], "solutions": []}


def _gemini_generate_reply(
    user_message: str,
    style: str,
    orgs: list[dict],
    projects: list[dict],
    history: list[dict] = None,
    lang: str = "uk",
) -> str:
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
Mention 1-3 organizations or projects from the list, but ONLY those that genuinely fit the topic of the user's message. If none of the listed orgs fit the topic, mention zero — do not pad the answer with off-topic links.
Format organization names as clickable Markdown links: [Name](url).
Keep it short and on-topic; obey the style profile's length limit."""
        no_orgs = "No specific organizations found."
        no_projs = "No specific projects found."
        user_prompt = f"""User message: "{user_message}"
{history_text}
Relevant organizations:
{org_list if org_list else no_orgs}

Relevant projects:
{proj_list if proj_list else no_projs}

Generate a short, on-topic response in the active style. Skip orgs that don't match the topic of this specific message."""
    else:
        system_prompt = f"""{style_instruction}
{resp_format}
Ти бот Hate-2-Action. Твоя задача — перетворювати обурення користувача на конкретні дії, рекомендуючи НГО та проєкти.
Відповідай тільки українською мовою.
Згадуй 1-3 організації або проєкти зі списку, але ЛИШЕ ті, що реально відповідають темі повідомлення користувача. Якщо жодна зі списку не підходить — не згадуй жодної, краще коротка відповідь без лінків, ніж довга з не-за-темою посиланнями.
Назви організацій оформлюй як клікабельні Markdown-посилання: [Назва](url).
Тримай відповідь короткою і по темі; дотримуйся обмеження довжини зі стилю."""
        user_prompt = f"""Повідомлення користувача: "{user_message}"
{history_text}
Релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

Релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Згенеруй коротку відповідь по темі в активному стилі. Не згадуй організації, що не стосуються теми саме цього повідомлення."""
    return _gemini_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_output_tokens=400,
    )


def _gemini_generate_org_reply(query: str, orgs: list[dict], projects: list[dict], style: str, lang: str = "uk") -> str:
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
    return _gemini_chat(
        [
            {"role": "system", "content": style_instruction},
            {"role": "user", "content": user_prompt},
        ],
        max_output_tokens=400,
    )


def _gemini_detect_style_from_message(message: str) -> str | None:
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
    result = _gemini_chat(
        [{"role": "user", "content": prompt}],
        max_output_tokens=10,
    ).strip().lower()
    return result if result in set(STYLE_PROFILES["uk"].keys()) else None


def _gemini_enrich_query(query: str) -> str:
    prompt = f"""Expand this query with relevant keywords and context for semantic search. Max 800 characters.
Query: "{query}"
Return only the enriched text."""
    text = _gemini_chat(
        [{"role": "user", "content": prompt}],
        max_output_tokens=150,
    )
    return text[:800]


def _gemini_rewrite_reply_with_style(text: str, style: str, lang: str = "uk", original_message: str | None = None) -> str:
    style_instruction = _style_instruction(style, lang)
    style_specific_en = ""
    style_specific_uk = ""
    if style == "funny":
        style_specific_en = (
            "Open the rewritten text with a joke, pun or witty observation about "
            "the situation — not with emotional validation. "
            "If the original starts with phrases like 'I see you're triggered', "
            "'this is eating you up', 'your anger is valid', REPLACE that opening "
            "with humor about the situation, not about the user's emotions. "
            "Don't tell the user how they feel. "
            "Aim for actual humor (wordplay, absurd comparison, self-irony), not "
            "just a friendly tone. "
            "Cut hard — final text should be 2-3 sentences max."
        )
        style_specific_uk = (
            "Починай переписаний текст з жарту або дотепного спостереження про "
            "ситуацію — не з емоційної валідації. "
            "Якщо оригінал починається фразами типу 'бачу, тебе тригернуло', "
            "'тебе вивертає', 'твоя злість зрозуміла', ЗАМІНИ цей вступ на гумор "
            "про ситуацію, а не про емоції користувача. "
            "Не кажи користувачу, що він відчуває. "
            "Цілься у справжній гумор (гра слів, абсурдне порівняння, самоіронія), "
            "а не просто дружній тон. Підсумок у кінці не має згадувати 'злість' "
            "чи 'обурення' користувача. "
            "Скорочуй сильно — фінальний текст 2-3 речення максимум."
        )
    elif style == "sarcastic":
        style_specific_en = (
            "Make sarcasm sharper and shorter — cut soft, hedging phrases and any "
            "long pep-talk endings. "
            "Mock the situation/system/absurdity, not the user. "
            "Do not narrate the user's emotions ('you're angry', 'you're upset'). "
            "A rhetorical question to the user is welcome. "
            "Helping is optional — if no listed org genuinely fits the topic, "
            "drop the org list entirely rather than padding. "
            "If the original user message contains profanity, you may match the "
            "register moderately. "
            "Final text: 2-3 sentences max."
        )
        style_specific_uk = (
            "Зроби сарказм гострішим і коротшим — приберай м'які, обережні "
            "формулювання та довгі мотиваційні кінцівки. "
            "Висміюй ситуацію/систему/абсурд, не самого користувача. "
            "Не коментуй емоції користувача ('ти злий', 'ти нервуєш', 'тебе обурює'). "
            "Доречне риторичне питання до користувача. "
            "Допомагати — необов'язково: якщо жодна організація зі списку не "
            "стосується теми, краще прибери блок з організаціями повністю, ніж "
            "вставляй не за темою. "
            "Якщо в оригінальному повідомленні користувача є нецензурна лексика, "
            "можна помірно вживати її і у відповіді (без особистих образ). "
            "Фінальний текст: 2-3 речення максимум."
        )
    elif style == "polite":
        style_specific_en = (
            "Soften the tone further — warm and supportive, not preachy. "
            "Start by briefly explaining why the user's concern is valid (the "
            "actual issue), then help with one practical step. "
            "Cut filler — final text 3-4 sentences."
        )
        style_specific_uk = (
            "Зроби тон ще м'якішим — теплий і підтримувальний, без повчань. "
            "На початку коротко поясни, чому скарга користувача справедлива (в чому "
            "суть проблеми), а потім допоможи одним практичним кроком. "
            "Прибери воду — фінальний текст 3-4 речення."
        )
    elif style == "rude":
        style_specific_en = (
            "Sharper, blunter, more direct — but never insult the user. "
            "Stay strictly on the topic of the user's message. "
            "Do NOT name specific cities, regions or countries that the user did "
            "not mention themselves — you don't know where the user is. "
            "Final text: 3-4 sentences."
        )
        style_specific_uk = (
            "Різкіше, грубіше, прямолінійніше — але без образ користувача. "
            "Тримайся строго теми повідомлення користувача. "
            "НЕ називай конкретних міст, областей чи країн, яких користувач сам не "
            "згадував — ти не знаєш, звідки користувач. "
            "Фінальний текст: 3-4 речення."
        )
    elif style == "normal":
        style_specific_en = (
            "Make it dry and matter-of-fact: state the problem briefly, list "
            "concrete options/steps, stop. No emotional validation, no pep talk. "
            "Final text: 3-4 sentences."
        )
        style_specific_uk = (
            "Сухо і по суті: коротко окресли проблему, перерахуй конкретні "
            "варіанти/кроки, і все. Без валідації емоцій, без підбадьорень. "
            "Фінальний текст: 3-4 речення."
        )
    if lang == "en":
        system_prompt = (
            f"{style_instruction}\n"
            "Rewrite the text in the given tone. Do not invent new facts. "
            "Preserve Markdown links, organization/project names and practical steps. "
            f"{style_specific_en} "
            "Return the final text in English only."
        )
        original_block = f"\n\nUser's original message (for context, do NOT rewrite it):\n{original_message}\n" if original_message else ""
        user_prompt = f"Original text:\n{text}{original_block}\n\nReturn only the final rewritten text."
    else:
        system_prompt = (
            f"{style_instruction}\n"
            "Перепиши текст у заданому тоні. Не вигадуй нових фактів. "
            "Збережи Markdown-посилання, назви організацій/проєктів і практичні кроки. "
            f"{style_specific_uk} "
            "Фінальний текст поверни лише українською мовою."
        )
        original_block = f"\n\nОригінальне повідомлення користувача (для контексту, не переписуй його):\n{original_message}\n" if original_message else ""
        user_prompt = f"Оригінальний текст:\n{text}{original_block}\n\nПоверни тільки фінальний переписаний текст."
    return _gemini_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_output_tokens=500,
    )
