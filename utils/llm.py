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
CHAT_MODEL = "gpt-4o-mini"
LANGUAGE_POLICY_UA = (
    "Відповідай виключно українською мовою. "
    "Не переходь на інші мови у звичайному тексті. "
    "Винятки: URL, офіційні назви організацій, технічні команди на кшталт /style_polite."
)
STYLE_PROFILES = {
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
}
RESPONSE_FORMAT = """
Дотримуйся структури відповіді:
1. Валідація — коротко визнай емоції чи занепокоєння користувача.
2. Твереза порада — дай реалістичний погляд і конкретні кроки.
3. Підбадьорення — заверши мотивуючим закликом до дії.
Відповідь має бути стислою (3-5 речень).
"""
def _style_instruction(style: str) -> str:
    normalized = style.strip().lower() if isinstance(style, str) else "normal"
    resolved = normalized if normalized in STYLE_PROFILES else "normal"
    description = STYLE_PROFILES[resolved]
    return (
        f"{LANGUAGE_POLICY_UA}\n"
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
    prompt = f"""Визнач, який пайплайн Telegram-бота має обробити нове повідомлення користувача.

Поверни рівно ОДНУ назву пайплайна:
- change_style
- show_orgs
- about_me
- problem_solution

Що робить кожен пайплайн:

1. change_style
Обирай, якщо користувач хоче змінити тон або формат відповідей бота.
Приклади наміру: змінити стиль, писати ввічливо, писати смішно, менше сарказму, коротше, простіше, формальніше.

2. show_orgs
Обирай, якщо користувач прямо просить знайти, показати або підібрати організації, фонди, ініціативи, контакти, гарячі лінії або місця, куди звернутися.
Також обирай цей варіант, якщо попереднє повідомлення бота просило назвати тему/категорію для пошуку організацій, а поточне повідомлення схоже саме на таку тему.

3. about_me
Обирай, якщо користувач питає, хто такий бот, що він уміє, як ним користуватися, які є команди, яка його мета або як він працює.

4. problem_solution
Обирай, якщо користувач описує проблему, обурення, конфлікт, несправедливість, стрес або безсилля і хоче зрозуміти, що робити далі.
Це основний пайплайн для скарг, емоційного контексту, запиту на практичні кроки, план дій або поради.

Правила маршрутизації:
- Якщо є явний запит на зміну стилю, обирай change_style навіть якщо в повідомленні є інші теми.
- Якщо користувач явно хоче список організацій, контакти, фонди, гарячі лінії або місця для звернення, обирай show_orgs.
- Якщо користувач переважно питає про бота та його можливості, обирай about_me.
- Якщо користувач описує проблему і питає, як діяти, що робити, як допомогти або як реагувати, обирай problem_solution, навіть якщо організації можуть знадобитися пізніше.
- Якщо є сумнів, обирай problem_solution.
- Ігноруй дрібні помилки, трансліт, суржик і змішані мови, якщо намір зрозумілий.

Контекст попереднього ходу розмови:
Попереднє повідомлення користувача: "{previous_message or ''}"
Попередня відповідь бота: "{previous_reply or ''}"
Попередній пайплайн: "{previous_pipeline_name}"

Нове повідомлення користувача:
"{message}"

Відповідай тільки назвою пайплайна без пояснень."""
    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
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
        max_tokens=600,
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
) -> str:
    """Generate a styled reply with org/project recommendations."""
    style_instruction = _style_instruction(style)
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:3]
    )
    proj_list = "\n".join(
        f"- {p['name']} від {p.get('org_name', 'невідома організація')}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:3]
    )
    history_text = ""
    if history:
        history_text = "\nОстанній контекст розмови:\n" + "\n".join(
            f"Користувач: {h['message_text']}\nБот: {h['reply_text']}" for h in history[-3:]
        )
    system_prompt = f"""{style_instruction}
{RESPONSE_FORMAT}
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
        max_tokens=400,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
def generate_org_reply(query: str, orgs: list[dict], projects: list[dict], style: str) -> str:
    """Generate a reply specifically for the Show Organizations pipeline."""
    style_instruction = _style_instruction(style)
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:5]
    )
    proj_list = "\n".join(
        f"- {p['name']} від {p.get('org_name', 'Н/Д')}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:5]
    )
    user_prompt = f"""Користувач шукає організації за темою: "{query}"

Ось релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

І релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Зроби корисний підсумок для 2-4 найрелевантніших організацій і як користувач може їх підтримати.
Використовуй Markdown-посилання: [Назва](url). Пиши стисло та практично."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": style_instruction},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=400,
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
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    return (
        result if result in set(STYLE_PROFILES.keys()) else None
    )
def enrich_query(query: str) -> str:
    """Expand a short query with keywords for better semantic search (max 800 chars)."""
    prompt = f"""Expand this query with relevant keywords and context for semantic search. Max 800 characters.
Query: "{query}"
Return only the enriched text."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()[:800]
def rewrite_reply_with_style(text: str, style: str) -> str:
    """Apply style as a post-generation filter while preserving content."""
    if style == "normal":
        return text
    style_instruction = _style_instruction(style)
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
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
