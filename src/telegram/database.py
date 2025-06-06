import sqlite3
import logging
import json
from typing import List, Tuple
from .config import Config

logger = logging.getLogger(__name__)

VECTOR_DIM = 1536

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def add_message(self, user_id: int, user_username: str, chat_title: str | None, text: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO messages (user_id, user_username, chat_title, text) "
                "VALUES (?, ?, ?, ?)",
                (user_id, user_username, chat_title, text)
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.Error as e:
            logger.error("DB insert failed: %s", e)
            return None

    def get_message_by_id(self, message_id: int) -> str | None:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT text FROM messages WHERE message_id = ?", (message_id,))
            row = cur.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error("DB query failed: %s", e)
            return None

    def upsert_problem(self, name: str, context: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT problem_id FROM problems WHERE name=? AND context=? LIMIT 1",
                (name, context)
            )
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO problems (name, context) VALUES (?, ?)",
                (name, context)
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.Error as e:
            logger.error("DB upsert failed: %s", e)
            return None

    def create_vec_tables_if_missing(self):
        cur = self.conn.cursor()
        cur.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_solutions
            USING vec0(
                solution_id   INTEGER PRIMARY KEY,
                embedding     float[{VECTOR_DIM}]
            );
        """)
        cur.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_projects
            USING vec0(
                project_id    INTEGER PRIMARY KEY,
                embedding     float[{VECTOR_DIM}]
            );
        """)
        cur.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_problems
            USING vec0(
                problem_id    INTEGER PRIMARY KEY,
                embedding     float[{VECTOR_DIM}]
            );
        """)
        self.conn.commit()

    def get_problems_by_ids(self, problem_ids: List[int]) -> List[Tuple[str, str]]:
        if not problem_ids:
            return []
        try:
            cur = self.conn.cursor()
            placeholders = ",".join("?" for _ in problem_ids)
            query = f"SELECT name, context FROM problems WHERE problem_id IN ({placeholders})"
            cur.execute(query, tuple(problem_ids))
            return cur.fetchall()
        except sqlite3.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_projects_by_ids(self, project_ids: List[int], top_n: int) -> List[Tuple[str, str, str, str]]:
        if not project_ids:
            return []
        try:
            cur = self.conn.cursor()
            selected_ids = project_ids[:top_n]
            placeholders = ",".join("?" for _ in selected_ids)
            query = (
                f"SELECT name, description, website, contact_email "
                f"FROM projects WHERE project_id IN ({placeholders})"
            )
            cur.execute(query, tuple(selected_ids))
            return cur.fetchall()
        except sqlite3.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def add_response(self, message_id: int, text: str):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO responses(message_id, text) VALUES (?, ?)",
                (message_id, text)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error("DB insert failed: %s", e)