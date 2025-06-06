# problem_detector.py

import os
import json
import sqlite3
import time
from typing import List, Dict

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

MODEL_NAME = "gpt-4"
MAX_RETRIES = 2
REQUEST_DELAY_SECONDS = 1

# -----------------------------------------------------------------------------
# Few‐shot examples for problem detection
# -----------------------------------------------------------------------------
EXAMPLES = [
    {
        "post": 'Він і пуйла називає харошим парнєм, лиш той "хароший парєнь" по вуха в крові українській',
        "json": {
            "problems": [
                {
                    "name": "Толерантність до воєнного злочинця",
                    "context": "Людина обурена, що хтось називає Путіна хорошим, ігноруючи його відповідальність за війну."
                },
                {
                    "name": "Знецінення українських жертв",
                    "context": "Пост нагадує про неприйнятність хвальби людини з кров’ю українців на руках."
                },
                {
                    "name": "Моральна апатія або необізнаність",
                    "context": "Користувач вказує, що деякі люди або не розуміють трагедії, або свідомо її ігнорують."
                }
            ]
        }
    },
    {
        "post": 'bbc.ua — мерзенний смітник, навіть коли опрацьовує важливу тему. За посиланням на статтю жодного слова немає про дітей Де Ніро, які зробили гендерний перехід. Тобто редактор вирішив, що особистість актора не достатньо цікава громадськості, треба ще клікбейту додати. В коментарях любителі вау-ефекта, яким взагалі до сраки, що там за посиланням.',
        "json": {
            "problems": [
                {
                    "name": "Сенсаційність у ЗМІ",
                    "context": "Автор обурений клікабельними заголовками замість об’єктивного викладу фактів."
                },
                {
                    "name": "Викривлення фактів",
                    "context": "Журналісти додають непідтверджені деталі, маніпулюючи довірою."
                },
                {
                    "name": "Знецінення приватного життя",
                    "context": "Критика втручання в особисте життя публічних осіб без згоди."
                },
                {
                    "name": "Поверхневість аудиторії",
                    "context": "Читачі реагують на заголовок, не читаючи статтю, що знижує критичне мислення."
                }
            ]
        }
    },
    {
        "post": 'Виховання йде від батьків дитини, але і вчителі повинні проводити бесіди, звертати увагу дітей на таку проблему. Що, ці ,,педагогині-богині" не бачили, що дітки цієї жінки дуже переживають?!! Бачили.... Бо бездушні, та жорстокі, байдужі до дітей, яких, так би мовити, вчать.',
        "json": {
            "problems": [
                {
                    "name": "Байдужість педагогів до дітей",
                    "context": "Вчителі не підтримують емоційно учнів у кризових ситуаціях."
                },
                {
                    "name": "Невиконання виховної функції школи",
                    "context": "Школа не займається морально-етичним вихованням учнів."
                },
                {
                    "name": "Психологічна травматизація дітей",
                    "context": "Відсутність уваги посилює почуття ізоляції та травму в дитини."
                },
                {
                    "name": "Критика системи освіти",
                    "context": "Гнів спрямований на всю освітню систему через байдужість персоналу."
                }
            ]
        }
    }
]

SCHEMA_HINT = '''
Відповідь має бути лише валідним JSON-об’єктом такої форми:
{
  "problems": [
    { "name": "<рядок>", "context": "<рядок>" },
    …
  ]
}
'''


def call_llm(prompt: str) -> str:
    """
    Uses LangChain’s ChatOpenAI to send a single system‐message prompt.
    Retries up to MAX_RETRIES on errors, with a short delay.
    """
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.1)
    for attempt in range(MAX_RETRIES + 1):
        try:
            response: AIMessage = llm([SystemMessage(content=prompt)])
            txt = response.content.strip()
            if txt.startswith("```json"):
                txt = txt.split("```json", 1)[1]
            if txt.endswith("```"):
                txt = txt.rsplit("```", 1)[0]
            return txt.strip()
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"LLM failed after {MAX_RETRIES} retries: {e}")
            time.sleep(REQUEST_DELAY_SECONDS)


def robust_json_load(raw: str, schema_hint: str) -> dict:
    """
    Attempts to parse `raw` as JSON. On failure, asks the LLM (via call_llm) to repair
    the JSON to fit SCHEMA_HINT, retrying up to MAX_RETRIES.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            txt = raw.strip()
            if txt.startswith("```json"):
                txt = txt.split("```json", 1)[1]
            if txt.endswith("```"):
                txt = txt.rsplit("```", 1)[0]
            return json.loads(txt)
        except json.JSONDecodeError as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"JSON parse failed after {MAX_RETRIES} retries: {e}")
            repair_prompt = (
                f"Попередня відповідь невалидний JSON ({e}).\n"
                f"JSON був:\n```json\n{raw}\n```\n"
                f"Надайте тільки валідний JSON за схемою:\n{schema_hint}"
            )
            raw = call_llm(repair_prompt)


def detect_problems_llm(message: str) -> List[Dict[str, str]]:
    """
    Builds a few‐shot prompt (with EXAMPLES & SCHEMA_HINT), sends it to gpt‐4 via LangChain,
    and returns a list of {"name", "context"} dicts.
    """
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.0)
    messages = [
        SystemMessage(content=(
            "Ти — експерт з аналізу дописів в соціальних мережах українською мовою. "
            "Витягни глибинні соціальні чи психологічні проблеми, які висловлює автор."
        ))
    ]

    # Insert example pairs
    for ex in EXAMPLES:
        messages.append(HumanMessage(content=f"Пост:\n{ex['post']}"))
        messages.append(AIMessage(content=json.dumps(ex["json"], ensure_ascii=False)))

    # Finally, the actual user post + schema hint
    messages.append(HumanMessage(content=f"Пост:\n{message}\n\n{SCHEMA_HINT}"))

    for attempt in range(MAX_RETRIES + 1):
        try:
            response: AIMessage = llm(messages)
            out = robust_json_load(response.content, SCHEMA_HINT)
            return out.get("problems", [])
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"LLM detection failed after {MAX_RETRIES} retries: {e}")
            time.sleep(REQUEST_DELAY_SECONDS)


def upsert_problem(cursor: sqlite3.Cursor, name: str, context: str) -> int:
    """
    If a problem with the same (name, context) exists already, return its ID;
    otherwise, insert a new row and return the new problem_id.
    """
    cursor.execute(
        "SELECT problem_id FROM problems WHERE name=? AND context=? LIMIT 1",
        (name, context)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO problems (name, context) VALUES (?, ?)",
        (name, context)
    )
    return cursor.lastrowid


def detect_problems(db_file: str, message_id: int) -> List[int]:
    """
    1) Fetch the message text by message_id from `messages`.
    2) Run detect_problems_llm(...) to get a list of {"name", "context"}.
    3) Upsert each problem into `problems(...)`.
    4) Return a list of all problem_id values inserted/updated.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # 1) Fetch original message text
    cur.execute("SELECT text FROM messages WHERE message_id = ?", (message_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Message ID {message_id} not found in DB")
    text = row[0].strip()

    # 2) Call LLM → list of problem dicts
    problems = detect_problems_llm(text)

    # 3) Upsert into `problems` and collect problem_ids
    ids: List[int] = []
    for p in problems:
        pid = upsert_problem(cur, p["name"], p["context"])
        ids.append(pid)

    conn.commit()
    conn.close()
    return ids
