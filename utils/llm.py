import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

STYLE_INSTRUCTIONS = {
    "polite": "Відповідай лише українською мовою. Тон теплий, ввічливий і підтримувальний.",
    "funny": "Відповідай лише українською мовою. Додай легкий гумор, але залишайся корисним.",
    "sarcastic": "Відповідай лише українською мовою. Використовуй стриманий сарказм, але веди користувача до дій.",
    "normal": "Відповідай лише українською мовою. Тон нейтральний, чіткий і збалансований.",
    "rude": "Відповідай лише українською мовою. Пиши різко і прямо, з практичними порадами.",
}

RESPONSE_FORMAT = """
Дотримуйся структури відповіді:
1. Валідація — коротко визнай емоції чи занепокоєння користувача.
2. Твереза порада — дай реалістичний погляд і конкретні кроки.
3. Підбадьорення — заверши мотивуючим закликом до дії.
Відповідь має бути стислою (3-5 речень).
"""


def get_embedding(text: str) -> list[float]:
    """Return a 1536-dim embedding for the given text."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text[:8000])
    return response.data[0].embedding


def detect_pipeline(message: str) -> str:
    """Classify the message intent into a pipeline name."""
    prompt = f"""Classify this Telegram bot message into exactly ONE of these categories:
- change_style (user wants to change response style/tone)
- show_orgs (user wants to find NGOs or organizations)
- about_me (user asks what the bot is or what it can do)
- process_message (user is complaining, ranting, or describing a problem)

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
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["normal"])

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
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["normal"])
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:5]
    )
    proj_list = "\n".join(
        f"- {p['name']} від {p.get('org_name', 'Н/Д')}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:5]
    )

    prompt = f"""{style_instruction}
Користувач шукає організації за темою: "{query}"

Ось релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

І релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Відповідай тільки українською мовою.
Зроби корисний підсумок для 2-4 найрелевантніших організацій і як користувач може їх підтримати.
Використовуй Markdown-посилання: [Назва](url). Пиши стисло та практично."""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def detect_style_from_message(message: str) -> str | None:
    """Try to detect which style the user is requesting."""
    prompt = f"""The user wants to change the response style of a bot. Which style are they asking for?
Options: polite, funny, sarcastic, normal, rude

Message: "{message}"

Respond with only the style name, or "unknown" if unclear."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    return result if result in {"polite", "funny", "sarcastic", "normal", "rude"} else None


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
