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


# ── CRUD: Organizations ──────────────────────────────────────────────────
def list_organizations() -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT organization_id, name, description, website, contact_email, created_at "
            "FROM organizations ORDER BY name"
        )
        return [dict(r) for r in cur.fetchall()]


def get_organization(organization_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT organization_id, name, description, website, contact_email, created_at "
            "FROM organizations WHERE organization_id = %s",
            (organization_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        org = dict(row)
        cur.execute(
            "SELECT project_id, name, description, organization_id, created_at "
            "FROM projects WHERE organization_id = %s ORDER BY name",
            (organization_id,),
        )
        org["projects"] = [dict(r) for r in cur.fetchall()]
        return org


def create_organization(name: str, description: str | None, website: str | None, contact_email: str | None) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO organizations (name, description, website, contact_email) "
            "VALUES (%s, %s, %s, %s) RETURNING *",
            (name, description, website, contact_email),
        )
        return dict(cur.fetchone())


def update_organization(organization_id: int, name: str, description: str | None, website: str | None, contact_email: str | None) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE organizations SET name = %s, description = %s, website = %s, contact_email = %s "
            "WHERE organization_id = %s RETURNING *",
            (name, description, website, contact_email, organization_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_organization(organization_id: int) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM organizations_solutions WHERE organization_id = %s", (organization_id,))
        cur.execute("DELETE FROM organizations_vec WHERE organization_id = %s", (organization_id,))
        cur.execute("UPDATE projects SET organization_id = NULL WHERE organization_id = %s", (organization_id,))
        cur.execute("DELETE FROM organizations WHERE organization_id = %s", (organization_id,))
        return cur.rowcount > 0


# ── CRUD: Projects ───────────────────────────────────────────────────────
def list_projects() -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT p.project_id, p.name, p.description, p.organization_id, p.created_at, "
            "       o.name AS organization_name "
            "FROM projects p LEFT JOIN organizations o ON p.organization_id = o.organization_id "
            "ORDER BY p.name"
        )
        return [dict(r) for r in cur.fetchall()]


def get_project(project_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT project_id, name, description, organization_id, created_at "
            "FROM projects WHERE project_id = %s",
            (project_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_project(name: str, description: str | None, organization_id: int | None) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO projects (name, description, organization_id) "
            "VALUES (%s, %s, %s) RETURNING *",
            (name, description, organization_id),
        )
        return dict(cur.fetchone())


def update_project(project_id: int, name: str, description: str | None, organization_id: int | None) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE projects SET name = %s, description = %s, organization_id = %s "
            "WHERE project_id = %s RETURNING *",
            (name, description, organization_id, project_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_project(project_id: int) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM projects_solutions WHERE project_id = %s", (project_id,))
        cur.execute("DELETE FROM projects_vec WHERE project_id = %s", (project_id,))
        cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
        return cur.rowcount > 0


# ── CRUD: Problems ───────────────────────────────────────────────────────
def list_problems() -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT problem_id, name, context, content, is_processed, created_at "
            "FROM problems ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]


def get_problem(problem_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT problem_id, name, context, content, is_processed, created_at "
            "FROM problems WHERE problem_id = %s",
            (problem_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_problem(name: str, context: str | None, content: str | None, is_processed: bool = False) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO problems (name, context, content, is_processed) "
            "VALUES (%s, %s, %s, %s) "
            "RETURNING problem_id, name, context, content, is_processed, created_at",
            (name, context, content, is_processed),
        )
        return dict(cur.fetchone())


def update_problem(problem_id: int, name: str, context: str | None, content: str | None, is_processed: bool | None) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE problems SET name = %s, context = %s, content = %s, "
            "is_processed = COALESCE(%s, is_processed) "
            "WHERE problem_id = %s "
            "RETURNING problem_id, name, context, content, is_processed, created_at",
            (name, context, content, is_processed, problem_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_problem(problem_id: int) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM problems_solutions WHERE problem_id = %s", (problem_id,))
        cur.execute("DELETE FROM problems WHERE problem_id = %s", (problem_id,))
        return cur.rowcount > 0


# ── CRUD: Solutions ──────────────────────────────────────────────────────
def list_solutions() -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT solution_id, name, context, content, created_at "
            "FROM solutions ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]


def get_solution(solution_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT solution_id, name, context, content, created_at "
            "FROM solutions WHERE solution_id = %s",
            (solution_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_solution(name: str, context: str | None, content: str | None) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO solutions (name, context, content) "
            "VALUES (%s, %s, %s) "
            "RETURNING solution_id, name, context, content, created_at",
            (name, context, content),
        )
        return dict(cur.fetchone())


def update_solution(solution_id: int, name: str, context: str | None, content: str | None) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE solutions SET name = %s, context = %s, content = %s "
            "WHERE solution_id = %s "
            "RETURNING solution_id, name, context, content, created_at",
            (name, context, content, solution_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_solution(solution_id: int) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM problems_solutions WHERE solution_id = %s", (solution_id,))
        cur.execute("DELETE FROM organizations_solutions WHERE solution_id = %s", (solution_id,))
        cur.execute("DELETE FROM projects_solutions WHERE solution_id = %s", (solution_id,))
        cur.execute("DELETE FROM solutions WHERE solution_id = %s", (solution_id,))
        return cur.rowcount > 0


# ── Messages ─────────────────────────────────────────────────────────────
def list_messages(limit: int = 200) -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT m.message_id, m.chat_id, m.user_id, m.message_text, m.reply_text, "
            "       m.pipeline_used, m.date, "
            "       u.username AS user_username, u.first_name AS user_first_name, "
            "       c.type AS chat_type "
            "FROM messages_history m "
            "LEFT JOIN users u ON m.user_id = u.user_id "
            "LEFT JOIN chats c ON m.chat_id = c.chat_id "
            "ORDER BY m.date DESC LIMIT %s",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_message(message_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT m.message_id, m.chat_id, m.user_id, m.message_text, m.reply_text, "
            "       m.pipeline_used, m.date, "
            "       u.username AS user_username, u.first_name AS user_first_name, "
            "       c.type AS chat_type "
            "FROM messages_history m "
            "LEFT JOIN users u ON m.user_id = u.user_id "
            "LEFT JOIN chats c ON m.chat_id = c.chat_id "
            "WHERE m.message_id = %s",
            (message_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
