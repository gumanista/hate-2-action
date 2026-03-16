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
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
def get_embedding(text: str) -> list[float]:
    """Return a 1536-dim embedding for the given text."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text[:8000])
    return response.data[0].embedding
def detect_pipeline(message: str) -> str:
    prompt = f"""Classify this Telegram bot message into exactly ONE intent category.

Categories and keyword hints:

1) change_style
Meaning: user wants to change bot tone, writing style, vibe, wording mode, or response format.
Keywords/phrases: style, tone, writing style, response style, change style, switch style, set style, rewrite in style, be polite, be funny, be sarcastic, be rude, neutral tone, formal tone, informal tone, less sarcasm, more humor, simple language, коротко, детальніше, простіше, стиль, тон, манера, формат відповіді, перефразуй, зміни стиль, зміни тон, пиши ввічливо, пиши смішно, пиши саркастично, пиши різко, пиши нейтрально, говори простіше, зроби коротше, не жартуй, більше жартів.

2) show_orgs
Meaning: user wants NGOs/organizations/charities/projects/initiatives, where to apply, where to ask for help, where to volunteer, who can help with an issue.
Keywords/phrases: NGO, NGOs, organization, organizations, non-profit, nonprofit, charity, charities, foundation, initiative, civil society, volunteer, volunteering, where to go, who can help, contacts, support center, hotline, legal aid, psychological help, shelters, human rights group, eco group, anti-corruption group, donor, grant, activism group, community group, НГО, громадська організація, організація, фонд, благодійність, ініціатива, волонтери, волонтерство, куди звернутися, хто допоможе, знайди організації, покажи організації, підбери НГО, контакти організацій, проєкти, активізм.

3) about_me
Meaning: user asks about bot identity, purpose, capabilities, limitations, how it works, what it can do.
Keywords/phrases: who are you, what are you, what is this bot, what can you do, help, commands, features, capabilities, how to use, how you work, what is Hate-2-Action, instructions, about bot, your role, your mission, хто ти, що ти вмієш, що це за бот, як користуватись, як ти працюєш, які команди, можливості бота, про бота, твоя роль, твоя місія, навіщо цей бот.

4) process_message
Meaning: user describes a personal/social problem, frustration, rant, complaint, conflict, injustice, anger, fear, stress, burnout, helplessness, asks for practical advice or actions.
Keywords/phrases: problem, issue, complaint, rant, angry, upset, frustrated, tired, hopeless, stuck, conflict, injustice, corruption, discrimination, violence, stress, anxiety, burnout, depression feelings, overwhelmed, what should I do, help me act, action plan, next steps, проблема, скарга, обурення, бісить, злість, несправедливість, корупція, дискримінація, насильство, тривога, стрес, вигорання, безсилля, не знаю що робити, порадь кроки, що робити далі.

Routing rules:
- Return exactly one category name: change_style, show_orgs, about_me, or process_message.
- If style-change intent is explicit, choose change_style even if other topics appear.
- If user asks primarily for organizations/where to apply/help contacts, choose show_orgs.
- If user asks mainly about bot identity/capabilities, choose about_me.
- Otherwise default to process_message.
- Treat minor typos, mixed alphabets, transliteration, and spelling noise as intended words.

Message: "{message}"

Respond with only the category name, nothing else."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    valid = {"change_style", "show_orgs", "about_me", "process_message"}
    return result if result in valid else "process_message"
def needs_org_category_clarification(message: str) -> bool:
    """Return True when org-search intent is present but topic/category is missing."""
    prompt = f"""Ти визначаєш, чи потрібно попросити користувача уточнити категорію
для пошуку організацій.

Поверни ТІЛЬКИ одне слово:
- clarify: якщо у повідомленні немає конкретної теми/категорії (наприклад, лише "покажи організації")
- proceed: якщо є конкретна тема (наприклад, "організації проти корупції", "climate NGOs", "освіта")

Правила:
- Враховуй дрібні помилки, опечатки, трансліт і змішані алфавіти.
- Якщо не впевнений, обирай clarify.

Повідомлення: "{message}"
"""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    if result == "proceed":
        return False
    if result == "clarify":
        return True
    return True
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
    response = client.chat.completions.create(
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
    response = client.chat.completions.create(
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
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
