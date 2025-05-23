import os
import sqlite3
import openai
import time
import sys
from typing import List, Set

# --- Configuration ---
MODEL = "gpt-4"             # or "gpt-3.5-turbo"
MAX_RETRIES = 2
REQUEST_DELAY_SECONDS = 1   # between retries

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
Напишіть розгорнуту відповідь українською мовою, в дусі і тоні користувача.
1. Підтвердьте розуміння його занепокоєнь.
2. Стисло згадайте основні виявлені проблеми.
3. Сформулюйте проєкти як конкретні шляхи вирішення — вкажіть назву, короткий опис і контактні дані.
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
                raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries: {e}") from e
            time.sleep(REQUEST_DELAY_SECONDS)
    raise RuntimeError("LLM call failed unexpectedly.")

def ensure_table(cursor: sqlite3.Cursor, table: str):
    """Check if a table exists in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    if not cursor.fetchone():
        raise RuntimeError(f"Table '{table}' is missing in database.")

def generate_output(db_file: str,
                    message_file: str,
                    problem_ids: List[int],
                    project_ids: List[int],
                    top_n: int = 5) -> str:
    """
    Generates a user-facing response based on detected problems and recommended projects.

    Args:
        db_file: Path to the SQLite database.
        message_file: Path to the user's message file.
        problem_ids: List of detected problem IDs.
        project_ids: List of recommended project IDs.
        top_n: The maximum number of top projects to include (default is 5).

    Returns:
        The generated response text.
    """
    # 0. Load API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    # 1. Load user message
    try:
        message = open(message_file, encoding="utf-8").read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Message file '{message_file}' not found.")

    # 2. Connect to DB and verify tables
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    for tbl in ("problems", "projects", "projects_solutions"):
        ensure_table(cur, tbl)

    # 3. Build the human-readable problems list directly from the passed-in IDs
    if problem_ids:
        placeholders = ",".join("?" for _ in problem_ids)
        cur.execute(
            f"SELECT name FROM problems WHERE problem_id IN ({placeholders})",
            problem_ids
        )
        names = [row[0] for row in cur.fetchall()]
        problems_list = "\n".join(f"{i+1}. {n}" for i, n in enumerate(names))
    else:
        problems_list = "Немає даних."

    # 4. Fetch top-N project details
    if project_ids:
        placeholders = ",".join("?" for _ in project_ids)
        # Preserve the original recommendation order via a CASE expression
        order_clause = " ".join(
            f"WHEN {pid} THEN {i}" for i, pid in enumerate(project_ids)
        )
        cur.execute(
            f"""
            SELECT project_id, name, description, website, contact_email
              FROM projects
             WHERE project_id IN ({placeholders})
             ORDER BY CASE project_id {order_clause} END
             LIMIT ?
            """,
            project_ids + [top_n]
        )
        proj_rows = cur.fetchall()
        projects_list = "\n\n".join(
            f"{r[1]}:\n{r[2] or 'Опис недоступний.'}\n"
            f"Веб: {r[3] or '—'}\nEmail: {r[4] or '—'}"
            for r in proj_rows
        )
    else:
        projects_list = "Немає рекомендованих проєктів."

    conn.close()

    # 5. Build final prompt and call LLM
    final_prompt = OUTPUT_TEMPLATE.format(
        message=message,
        problems_list=problems_list,
        projects_list=projects_list
    )
    return call_llm(final_prompt)

# If this module is run directly for local testing:
if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "donation.db"
    msg = sys.argv[2] if len(sys.argv) > 2 else "message.txt"
    # In real usage, CLI should pass in the detected problem_ids and project_ids:
    example_problem_ids = [61, 65, 66]
    example_project_ids = [1, 2, 3, 4, 5]
    print(generate_output(db, msg, example_problem_ids, example_project_ids))
