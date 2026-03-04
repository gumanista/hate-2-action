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

# Standard library import for environment variable access.
import os
# Standard library import for JSON parsing.
import json
# Official OpenAI Python SDK client.
from openai import OpenAI
# Utility to load environment variables from `.env`.
from dotenv import load_dotenv

# Load `.env` file into process environment.
load_dotenv()

# Initialize OpenAI client using API key from environment.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Embedding model used for semantic search vectors.
EMBEDDING_MODEL = "text-embedding-3-small"
# Chat/completions model used for classification and text generation.
CHAT_MODEL = "gpt-4o-mini"

# Tone presets keyed by style id used across response generation functions.
STYLE_INSTRUCTIONS = {
    # Polite tone instruction.
    "polite": "Відповідай лише українською мовою. Тон теплий, ввічливий і підтримувальний.",
    # Funny tone instruction.
    "funny": "Відповідай лише українською мовою. Додай легкий гумор, але залишайся корисним.",
    # Sarcastic tone instruction.
    "sarcastic": "Відповідай лише українською мовою. Використовуй стриманий сарказм, але веди користувача до дій.",
    # Neutral tone instruction.
    "normal": "Відповідай лише українською мовою. Тон нейтральний, чіткий і збалансований.",
    # Rude/direct tone instruction.
    "rude": "Відповідай лише українською мовою. Пиши різко і прямо, з практичними порадами.",
}

# Shared structure instruction appended to generation prompts.
RESPONSE_FORMAT = """
Дотримуйся структури відповіді:
1. Валідація — коротко визнай емоції чи занепокоєння користувача.
2. Твереза порада — дай реалістичний погляд і конкретні кроки.
3. Підбадьорення — заверши мотивуючим закликом до дії.
Відповідь має бути стислою (3-5 речень).
"""


# Generate embedding vector for semantic similarity operations.
def get_embedding(text: str) -> list[float]:
    """Return a 1536-dim embedding for the given text."""
    # Call embeddings API with an input cap to avoid oversized payloads.
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text[:8000])
    # Return embedding array from first result item.
    return response.data[0].embedding


# Classify raw user message into one orchestrator pipeline label.
def detect_pipeline(message: str) -> str:
    """Classify the message intent into a pipeline name."""
    # Build strict classification prompt with allowed categories.
    prompt = f"""Classify this Telegram bot message into exactly ONE of these categories:
- change_style (user wants to change response style/tone)
- show_orgs (user wants to find NGOs or organizations)
- about_me (user asks what the bot is or what it can do)
- process_message (user is complaining, ranting, or describing a problem)

Message: "{message}"

Respond with only the category name, nothing else."""
    # Request deterministic classification from chat model.
    response = client.chat.completions.create(
        # Use shared chat model constant.
        model=CHAT_MODEL,
        # Send a single user message containing the task prompt.
        messages=[{"role": "user", "content": prompt}],
        # Small token budget because output is one label.
        max_tokens=20,
        # Zero temperature for stable class selection.
        temperature=0,
    )
    # Normalize model output for robust comparison.
    result = response.choices[0].message.content.strip().lower()
    # Set of accepted orchestrator labels.
    valid = {"change_style", "show_orgs", "about_me", "process_message"}
    # Return valid label or safe fallback.
    return result if result in valid else "process_message"


# Extract structured problem and solution entities from complaint text.
def extract_problems_and_solutions(message: str) -> dict:
    """Extract problems and solutions from a user complaint using LLM."""
    # Prompt model to return strict JSON schema with `problems` and `solutions` arrays.
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
    # Request JSON-formatted extraction from model.
    response = client.chat.completions.create(
        # Use shared chat model constant.
        model=CHAT_MODEL,
        # Send extraction prompt as user message.
        messages=[{"role": "user", "content": prompt}],
        # Provide enough tokens for a small structured JSON response.
        max_tokens=600,
        # Low temperature for stable schema adherence.
        temperature=0.2,
        # Enforce JSON object format from model API.
        response_format={"type": "json_object"},
    )
    # Parse JSON string into Python dictionary.
    return json.loads(response.choices[0].message.content)


# Generate full response for problem-solution flow with recommendations.
def generate_reply(
    # Original user message text.
    user_message: str,
    # Active response style id.
    style: str,
    # Ranked organization candidates.
    orgs: list[dict],
    # Ranked project candidates.
    projects: list[dict],
    # Optional recent conversation history.
    history: list[dict] = None,
) -> str:
    """Generate a styled reply with org/project recommendations."""
    # Resolve style instruction with fallback to neutral style.
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["normal"])

    # Render up to 3 organization candidates as bullet list for prompt context.
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:3]
    )
    # Render up to 3 project candidates as bullet list for prompt context.
    proj_list = "\n".join(
        f"- {p['name']} від {p.get('org_name', 'невідома організація')}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:3]
    )

    # Default empty history text when no chat context is available.
    history_text = ""
    # Include the last up to 3 dialogue turns when history exists.
    if history:
        # Build readable context block for the model.
        history_text = "\nОстанній контекст розмови:\n" + "\n".join(
            f"Користувач: {h['message_text']}\nБот: {h['reply_text']}" for h in history[-3:]
        )

    # Construct system prompt defining style, mission, structure, and formatting rules.
    system_prompt = f"""{style_instruction}
{RESPONSE_FORMAT}
Ти бот Hate-2-Action. Твоя задача — перетворювати обурення користувача на конкретні дії, рекомендуючи НГО та проєкти.
Відповідай тільки українською мовою.
Завжди згадай 2-3 релевантні організації або проєкти зі списку.
Назви організацій оформлюй як клікабельні Markdown-посилання: [Назва](url)"""

    # Construct user prompt with message, history, and retrieved candidates.
    user_prompt = f"""Повідомлення користувача: "{user_message}"
{history_text}
Релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

Релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Згенеруй відповідь за схемою: валідація → порада → підбадьорення."""

    # Ask model to generate final reply using two-message prompt setup.
    response = client.chat.completions.create(
        # Use shared chat model constant.
        model=CHAT_MODEL,
        # Provide system and user instructions separately.
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        # Response token budget for concise but complete answer.
        max_tokens=400,
        # Higher temperature for natural conversational output.
        temperature=0.7,
    )
    # Return trimmed response text.
    return response.choices[0].message.content.strip()


# Generate response specifically for organization-category lookup flow.
def generate_org_reply(query: str, orgs: list[dict], projects: list[dict], style: str) -> str:
    """Generate a reply specifically for the Show Organizations pipeline."""
    # Resolve style instruction with fallback to neutral style.
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["normal"])
    # Render up to 5 organization candidates for prompt context.
    org_list = "\n".join(
        f"- {o['name']}: {o.get('description', '')} ({o.get('website', '')})"
        for o in orgs[:5]
    )
    # Render up to 5 project candidates for prompt context.
    proj_list = "\n".join(
        f"- {p['name']} від {p.get('org_name', 'Н/Д')}: {p.get('description', '')} ({p.get('org_website', '')})"
        for p in projects[:5]
    )

    # Build single prompt instructing summary + actionable guidance.
    prompt = f"""{style_instruction}
Користувач шукає організації за темою: "{query}"

Ось релевантні організації:
{org_list if org_list else "Конкретних організацій не знайдено."}

І релевантні проєкти:
{proj_list if proj_list else "Конкретних проєктів не знайдено."}

Відповідай тільки українською мовою.
Зроби корисний підсумок для 2-4 найрелевантніших організацій і як користувач може їх підтримати.
Використовуй Markdown-посилання: [Назва](url). Пиши стисло та практично."""

    # Request generated answer from model.
    response = client.chat.completions.create(
        # Use shared chat model constant.
        model=CHAT_MODEL,
        # Send single user prompt.
        messages=[{"role": "user", "content": prompt}],
        # Response token budget.
        max_tokens=400,
        # Creative but controlled tone.
        temperature=0.7,
    )
    # Return trimmed generated text.
    return response.choices[0].message.content.strip()


# Detect requested style name from free-form user text.
def detect_style_from_message(message: str) -> str | None:
    """Try to detect which style the user is requesting."""
    # Build classification prompt with fixed style options.
    prompt = f"""The user wants to change the response style of a bot. Which style are they asking for?
Options: polite, funny, sarcastic, normal, rude

Message: "{message}"

Respond with only the style name, or "unknown" if unclear."""
    # Request deterministic style classification.
    response = client.chat.completions.create(
        # Use shared chat model constant.
        model=CHAT_MODEL,
        # Send style detection prompt.
        messages=[{"role": "user", "content": prompt}],
        # Very small token budget for one label.
        max_tokens=10,
        # Zero temperature for stable output.
        temperature=0,
    )
    # Normalize output label.
    result = response.choices[0].message.content.strip().lower()
    # Return style when recognized, else `None`.
    return (
        result
        if result in {"polite", "funny", "sarcastic", "normal", "rude"}
        else None
    )


# Expand short category query into richer semantic-search text.
def enrich_query(query: str) -> str:
    """Expand a short query with keywords for better semantic search (max 800 chars)."""
    # Build prompt asking model to add keywords/context while staying concise.
    prompt = f"""Expand this query with relevant keywords and context for semantic search. Max 800 characters.
Query: "{query}"
Return only the enriched text."""
    # Request expanded query text from model.
    response = client.chat.completions.create(
        # Use shared chat model constant.
        model=CHAT_MODEL,
        # Send enrichment prompt.
        messages=[{"role": "user", "content": prompt}],
        # Token budget suitable for short expansion.
        max_tokens=150,
        # Low creativity for focused keyword expansion.
        temperature=0.3,
    )
    # Return enriched text trimmed to hard 800-char cap.
    return response.choices[0].message.content.strip()[:800]
