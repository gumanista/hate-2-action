# src/output_generator.py

import os
import sqlite3
import openai
import time
from typing import List

MODEL = "gpt-4"
MAX_RETRIES = 2
REQUEST_DELAY_SECONDS = 1

OUTPUT_TEMPLATE = '''
You are a Ukrainian-language chatbot responding in the same style as the user.

Користувач написав:
\"\"\"{message}\"\"\"

Виявлені проблеми:
{problems_list}

Рекомендовані для підтримки проєкти:
{projects_list}

ІНСТРУКЦІЯ:
1. Підтвердьте, що ви зрозуміли занепокоєння.
2. Стисло перераховуйте проблеми.
3. Опишіть проєкти як рішення: назва, опис, контакти.
4. Закличте підтримати донатом.
'''

def call_llm(prompt: str) -> str:
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = openai.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                # strip code fences
                lines = text.splitlines()
                text = "\n".join(lines[1:-1])
            return text
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"LLM call failed: {e}")
            time.sleep(REQUEST_DELAY_SECONDS)

def generate_output(
    db_file: str,
    message_id: int,
    problem_ids: List[int],
    project_ids: List[int],
    top_n: int = 5
) -> str:
    """
    1) Loads message text from messages WHERE message_id
    2) Builds problems_list & projects_list from DB
    3) Calls LLM to craft the reply
    4) Inserts the reply into responses table
    5) Returns the reply text
    """
    # 0) API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    conn = sqlite3.connect(db_file)
    cur  = conn.cursor()

    # 1) Fetch user message
    cur.execute("SELECT text FROM messages WHERE message_id = ?", (message_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Message ID {message_id} not found in DB")
    message = row[0].strip()

    # 2) Build problems list
    if problem_ids:
        ph = ",".join("?" for _ in problem_ids)
        cur.execute(f"SELECT name FROM problems WHERE problem_id IN ({ph})", problem_ids)
        names = [r[0] for r in cur.fetchall()]
        problems_list = "\n".join(f"{i+1}. {n}" for i, n in enumerate(names))
    else:
        problems_list = "Немає виявлених проблем."

    # 3) Build projects list
    if project_ids:
        ph = ",".join("?" for _ in project_ids)
        order_clause = " ".join(f"WHEN {pid} THEN {i}" for i, pid in enumerate(project_ids))
        cur.execute(
            f"""
            SELECT name, description, website, contact_email
              FROM projects
             WHERE project_id IN ({ph})
             ORDER BY CASE project_id {order_clause} END
             LIMIT ?
            """,
            project_ids + [top_n]
        )
        rows = cur.fetchall()
        projects_list = "\n\n".join(
            f"{idx+1}. {name}\nОпис: {desc or '—'}\nВеб: {site or '—'}\nEmail: {email or '—'}"
            for idx, (name, desc, site, email) in enumerate(rows)
        )
    else:
        projects_list = "Немає рекомендованих проєктів."

    conn.close()

    # 4) Call LLM
    prompt = OUTPUT_TEMPLATE.format(
        message=message,
        problems_list=problems_list,
        projects_list=projects_list
    )
    reply = call_llm(prompt)

    # 5) Persist into responses
    conn2 = sqlite3.connect(db_file)
    cur2  = conn2.cursor()
    cur2.execute(
        "INSERT INTO responses (message_id, text) VALUES (?, ?)",
        (message_id, reply)
    )
    conn2.commit()
    conn2.close()

    return reply
