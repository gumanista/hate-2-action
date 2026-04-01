import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from dotenv import load_dotenv
from db.config import DEFAULT_DATABASE_URL, get_database_url

load_dotenv()
DATABASE_URL = get_database_url(DEFAULT_DATABASE_URL)


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        cur.execute(
            "INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s) RETURNING *",
            (user_id, username, first_name),
        )
        return dict(cur.fetchone())


def get_user_style(user_id: int) -> str:
    with db_cursor() as cur:
        cur.execute("SELECT response_style FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row["response_style"] if row else "normal"


def set_user_style(user_id: int, style: str):
    with db_cursor() as cur:
        cur.execute(
            "UPDATE users SET response_style = %s WHERE user_id = %s",
            (style, user_id),
        )

def get_or_create_chat(chat_id: int, chat_type: str) -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM chats WHERE chat_id = %s", (chat_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        cur.execute(
            "INSERT INTO chats (chat_id, type) VALUES (%s, %s) RETURNING *",
            (chat_id, chat_type),
        )
        return dict(cur.fetchone())


def get_chat_style(chat_id: int) -> str | None:
    with db_cursor() as cur:
        cur.execute("SELECT response_style FROM chats WHERE chat_id = %s", (chat_id,))
        row = cur.fetchone()
        return row["response_style"] if row else None

def save_message(
    chat_id: int,
    user_id: int,
    message_text: str,
    reply_text: str,
    tg_message_id: int = None,
    pipeline_used: str = None,
):
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO messages_history
               (chat_id, user_id, tg_message_id, message_text, reply_text, pipeline_used)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (chat_id, user_id, tg_message_id, message_text, reply_text, pipeline_used),
        )


def get_chat_history(chat_id: int, user_id: int = None, limit: int = 10) -> list[dict]:
    with db_cursor() as cur:
        if user_id:
            cur.execute(
                """SELECT message_text, reply_text FROM messages_history
                   WHERE chat_id = %s AND user_id = %s
                   ORDER BY date DESC LIMIT %s""",
                (chat_id, user_id, limit),
            )
        else:
            cur.execute(
                """SELECT message_text, reply_text FROM messages_history
                   WHERE chat_id = %s
                   ORDER BY date DESC LIMIT %s""",
                (chat_id, limit),
            )
        return [dict(r) for r in cur.fetchall()][::-1]


def get_last_message_context(chat_id: int, user_id: int = None) -> dict | None:
    with db_cursor() as cur:
        if user_id:
            cur.execute(
                """SELECT message_text, reply_text, pipeline_used
                   FROM messages_history
                   WHERE chat_id = %s AND user_id = %s
                   ORDER BY date DESC
                   LIMIT 1""",
                (chat_id, user_id),
            )
        else:
            cur.execute(
                """SELECT message_text, reply_text, pipeline_used
                   FROM messages_history
                   WHERE chat_id = %s
                   ORDER BY date DESC
                   LIMIT 1""",
                (chat_id,),
            )
        row = cur.fetchone()
        return dict(row) if row else None

def upsert_problem(name: str, context: str, content: str, embedding: list[float]) -> int:
    """Insert a problem if cosine similarity to existing ones is below threshold."""
    with db_cursor() as cur:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        cur.execute(
            """SELECT problem_id, 1 - (embedding <=> %s::vector) AS similarity
               FROM problems
               WHERE embedding IS NOT NULL
               ORDER BY embedding <=> %s::vector
               LIMIT 1""",
            (embedding_str, embedding_str),
        )
        row = cur.fetchone()
        if row and row["similarity"] > 0.92:
            return row["problem_id"]  # reuse existing problem
        cur.execute(
            """INSERT INTO problems (name, context, content, embedding)
               VALUES (%s, %s, %s, %s::vector) RETURNING problem_id""",
            (name, context, content, embedding_str),
        )
        return cur.fetchone()["problem_id"]


def upsert_solution(name: str, context: str, content: str, embedding: list[float]) -> int:
    """Insert a solution if not a near-duplicate."""
    with db_cursor() as cur:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        cur.execute(
            """SELECT solution_id, 1 - (embedding <=> %s::vector) AS similarity
               FROM solutions
               WHERE embedding IS NOT NULL
               ORDER BY embedding <=> %s::vector
               LIMIT 1""",
            (embedding_str, embedding_str),
        )
        row = cur.fetchone()
        if row and row["similarity"] > 0.92:
            return row["solution_id"]
        cur.execute(
            """INSERT INTO solutions (name, context, content, embedding)
               VALUES (%s, %s, %s, %s::vector) RETURNING solution_id""",
            (name, context, content, embedding_str),
        )
        return cur.fetchone()["solution_id"]


def link_problem_solution(problem_id: int, solution_id: int, score: float):
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO problems_solutions (problem_id, solution_id, similarity_score)
               VALUES (%s, %s, %s)
               ON CONFLICT (problem_id, solution_id) DO UPDATE SET similarity_score = EXCLUDED.similarity_score""",
            (problem_id, solution_id, score),
        )

def find_orgs_by_embedding(embedding: list[float], top_n: int = 5) -> list[dict]:
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    with db_cursor() as cur:
        cur.execute(
            """SELECT o.organization_id, o.name, o.description, o.website,
                      1 - (ov.embedding <=> %s::vector) AS similarity
               FROM organizations o
               JOIN organizations_vec ov ON o.organization_id = ov.organization_id
               WHERE ov.embedding IS NOT NULL
               ORDER BY ov.embedding <=> %s::vector
               LIMIT %s""",
            (embedding_str, embedding_str, top_n),
        )
        return [dict(r) for r in cur.fetchall()]


def find_projects_by_embedding(embedding: list[float], top_n: int = 5) -> list[dict]:
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    with db_cursor() as cur:
        cur.execute(
            """SELECT p.project_id, p.name, p.description,
                      o.name AS org_name, o.website AS org_website,
                      1 - (pv.embedding <=> %s::vector) AS similarity
               FROM projects p
               JOIN projects_vec pv ON p.project_id = pv.project_id
               LEFT JOIN organizations o ON p.organization_id = o.organization_id
               WHERE pv.embedding IS NOT NULL
               ORDER BY pv.embedding <=> %s::vector
               LIMIT %s""",
            (embedding_str, embedding_str, top_n),
        )
        return [dict(r) for r in cur.fetchall()]


def find_orgs_via_solutions(problem_ids: list[int], top_n: int = 5) -> list[dict]:
    """Ranked orgs by chaining problems→solutions→organizations similarity scores."""
    if not problem_ids:
        return []
    placeholders = ",".join(["%s"] * len(problem_ids))
    with db_cursor() as cur:
        cur.execute(
            f"""SELECT o.organization_id, o.name, o.description, o.website,
                       SUM(ps.similarity_score * os.similarity_score) AS combined_score
                FROM problems_solutions ps
                JOIN organizations_solutions os ON ps.solution_id = os.solution_id
                JOIN organizations o ON os.organization_id = o.organization_id
                WHERE ps.problem_id IN ({placeholders})
                GROUP BY o.organization_id, o.name, o.description, o.website
                ORDER BY combined_score DESC
                LIMIT %s""",
            (*problem_ids, top_n),
        )
        return [dict(r) for r in cur.fetchall()]


def find_projects_via_solutions(problem_ids: list[int], top_n: int = 5) -> list[dict]:
    if not problem_ids:
        return []
    placeholders = ",".join(["%s"] * len(problem_ids))
    with db_cursor() as cur:
        cur.execute(
            f"""SELECT p.project_id, p.name, p.description,
                       o.name AS org_name, o.website AS org_website,
                       SUM(ps.similarity_score * prs.similarity_score) AS combined_score
                FROM problems_solutions ps
                JOIN projects_solutions prs ON ps.solution_id = prs.solution_id
                JOIN projects p ON prs.project_id = p.project_id
                LEFT JOIN organizations o ON p.organization_id = o.organization_id
                WHERE ps.problem_id IN ({placeholders})
                GROUP BY p.project_id, p.name, p.description, o.name, o.website
                ORDER BY combined_score DESC
                LIMIT %s""",
            (*problem_ids, top_n),
        )
        return [dict(r) for r in cur.fetchall()]
