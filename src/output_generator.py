import os
import sqlite3
import openai
import time
import sys
from typing import List

# --- Configuration ---
# MODEL and MAX_RETRIES are used by call_llm, keep them here
MODEL = "gpt-4"           # or "gpt-3.5-turbo"
MAX_RETRIES = 2
REQUEST_DELAY_SECONDS = 1  # between retries

# --- Prompt Template for Final Output ---
OUTPUT_TEMPLATE = '''
You are a Ukrainian-language chatbot responding in the same style as the user.

Користувач написав:
\"\"\"{message}\"\"\"

Виявлені проблеми:
{problems_list}

Рекомендовані для підтримки проєкти:
{projects_list}

ІНСТРУКЦІЯ:
Напишіть розгорнену відповідь українською мовою, в дусі і тоні користувача.
1. Підтвердьте розуміння його занепокоєнь.
2. Стисло згадайте основні виявлені проблеми.
3. Представте проєкти як конкретні шляхи вирішення — вкажіть назву, короткий опис і контактні дані.
4. Закінчіть закликом зробити донат та підтримати ці проєкти.
'''

def call_llm(prompt: str) -> str:
    """Call OpenAI chat completion with retries."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = openai.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            text = resp.choices[0].message.content.strip()
            # strip fences if present
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            return text
        except Exception as e:
            if attempt == MAX_RETRIES:
                # Re-raise the exception after the last attempt
                raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries: {e}") from e
            time.sleep(REQUEST_DELAY_SECONDS)
    # This part should not be reached if MAX_RETRIES >= 0, but added for completeness
    raise RuntimeError("LLM call failed unexpectedly.")


def ensure_table(cursor, table: str):
    """Check if a table exists in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    if not cursor.fetchone():
        # In the refactored function, we raise an error instead of exiting
        raise RuntimeError(f"Table '{table}' is missing in database.")


def generate_output(db_file: str,
                    message_file: str,
                    project_ids: List[int],
                    top_n: int = 5) -> str:
    """
    Generates a user-facing response based on detected problems and recommended projects.

    Args:
        db_file: Path to the SQLite database.
        message_file: Path to the user's message file.
        project_ids: List of recommended project IDs.
        top_n: The maximum number of top projects to include (default is 5).

    Returns:
        The generated response text.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        # In the refactored function, we raise an error instead of exiting
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    # 1. Load user message
    try:
        message = open(message_file, encoding="utf-8").read().strip()
    except FileNotFoundError:
        # In the refactored function, we raise an error instead of exiting
        raise FileNotFoundError(f"Message file '{message_file}' not found.")

    # problem_ids are not used in this function, only project_ids are needed.
    # The original main function loaded problem_ids from a file, but the new
    # function signature doesn't include problem_ids as an argument.
    # Assuming problem names are not needed for the final output based on the
    # provided function signature and the original prompt template which only
    # uses {problems_list} which was populated from problem names fetched from DB.
    # If problem names are needed, the problem_ids should be passed as an argument
    # to this function. For now, I will omit fetching problem names.
    problems_list = "Немає даних." # Default if problem names are not fetched

    # 2. Connect to DB and verify tables
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    try:
        for tbl in ("problems", "projects", "projects_solutions"):
            ensure_table(cur, tbl)

        # 3. Fetch top projects by similarity_score
        proj_rows = []
        if project_ids:
            placeholders = ",".join("?" for _ in project_ids)
            # get max similarity per project, then pick top N
            cur.execute(f"""
                SELECT p.project_id, p.name, p.description, p.website, p.contact_email,
                       MAX(ps.similarity_score) AS score
                FROM projects p
                JOIN projects_solutions ps ON p.project_id = ps.project_id
                WHERE p.project_id IN ({placeholders})
                GROUP BY p.project_id
                ORDER BY score DESC
                LIMIT ?
            """, project_ids + [top_n]) # Pass top_n as a parameter

            proj_rows = cur.fetchall()

        if not proj_rows:
            projects_list = "Немає даних."
        else:
            # Format: "1. Name — Description (веб:..., email:...)"
            formatted = []
            for idx, (pid, name, desc, site, email, score) in enumerate(proj_rows, start=1):
                parts = [f"{idx}. {name}", desc or ""]
                contact = []
                if site:  contact.append(f"веб: {site}")
                if email: contact.append(f"email: {email}")
                if contact:
                    parts.append("(" + "; ".join(contact) + ")")
                formatted.append(" — ".join(p for p in parts if p))
            projects_list = "\n".join(formatted)

    finally:
        conn.close()

    # 4. Generate final response
    prompt = OUTPUT_TEMPLATE.format(
        message=message,
        problems_list=problems_list, # This will be "Немає даних." as problem names are not fetched
        projects_list=projects_list
    )

    # 5. Call LLM and return the reply
    reply = call_llm(prompt)
    return reply

# Note: The __main__ block from the original script is not included here
# as this file is intended to be imported and used as a module.