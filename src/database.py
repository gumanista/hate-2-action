import sqlite3
import logging
import json
from typing import List, Tuple
from typing import Any
from langchain_community.embeddings import OpenAIEmbeddings

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

    def upsert_solution(self, name: str, context: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT solution_id FROM solutions WHERE name=? AND context=? LIMIT 1",
                (name, context)
            )
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO solutions (name, context) VALUES (?, ?)",
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

    def embed_new_solutions_and_projects(self, embedder: OpenAIEmbeddings) -> Tuple[List[int], List[int]]:
        cur = self.conn.cursor()

        # --- Solutions ---
        cur.execute("SELECT solution_id FROM solutions;")
        all_solution_ids = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT solution_id FROM vec_solutions;")
        embedded_solution_ids = {row[0] for row in cur.fetchall()}
        new_solution_ids = list(all_solution_ids - embedded_solution_ids)

        if new_solution_ids:
            placeholders = ",".join("?" * len(new_solution_ids))
            cur.execute(f"SELECT solution_id, context FROM solutions WHERE solution_id IN ({placeholders})", new_solution_ids)
            rows_to_embed = cur.fetchall()
            for sid, context in rows_to_embed:
                if not context:
                    continue
                vec = embedder.embed_documents([context])[0]
                cur.execute("INSERT OR REPLACE INTO vec_solutions(solution_id, embedding) VALUES (?, json(?));", (sid, json.dumps(vec)))
            self.conn.commit()

        # --- Projects ---
        cur.execute("SELECT project_id FROM projects;")
        all_project_ids = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT project_id FROM vec_projects;")
        embedded_project_ids = {row[0] for row in cur.fetchall()}
        new_project_ids = list(all_project_ids - embedded_project_ids)

        if new_project_ids:
            placeholders = ",".join("?" * len(new_project_ids))
            cur.execute(f"SELECT project_id, description FROM projects WHERE project_id IN ({placeholders})", new_project_ids)
            rows_to_embed = cur.fetchall()
            for pid, desc in rows_to_embed:
                if not desc:
                    continue
                vec = embedder.embed_documents([desc])[0]
                cur.execute("INSERT OR REPLACE INTO vec_projects(project_id, embedding) VALUES (?, json(?));", (pid, json.dumps(vec)))
            self.conn.commit()

        return new_solution_ids, new_project_ids

    def match_new_solutions_to_projects(self, new_solution_ids: List[int], k_proj: int = 5):
        if not new_solution_ids:
            return

        cur = self.conn.cursor()
        for sid in new_solution_ids:
            sql = f"""
            WITH target AS (
              SELECT embedding
              FROM vec_solutions
              WHERE solution_id = {sid}
            )
            SELECT
              vp.project_id,
              1.0 - distance as similarity
            FROM vec_projects AS vp, target
            WHERE vp.embedding
                  MATCH target.embedding
                AND k = {k_proj};
            """
            cur.execute(sql)
            matches = cur.fetchall()

            for project_id, similarity_score in matches:
                cur.execute(
                    "INSERT OR IGNORE INTO projects_solutions(project_id, solution_id, similarity_score) VALUES (?, ?, ?)",
                    (project_id, sid, similarity_score)
                )
        self.conn.commit()

    def embed_and_match_new_problems(self, embedder: OpenAIEmbeddings, problem_ids: List[int], k: int = 5) -> List[int]:
        cur = self.conn.cursor()
        matched_solution_ids = []

        for pid in problem_ids:
            cur.execute("SELECT context FROM problems WHERE problem_id = ?", (pid,))
            row = cur.fetchone()
            if row is None:
                continue
            problem_text = row[0]

            vec = embedder.embed_documents([problem_text])[0]
            cur.execute(
                "INSERT OR REPLACE INTO vec_problems(problem_id, embedding) VALUES (?, json(?));",
                (pid, json.dumps(vec))
            )
            self.conn.commit()

            sql = f"""
            WITH target AS (
              SELECT embedding
              FROM vec_problems
              WHERE problem_id = {pid}
            )
            INSERT OR IGNORE INTO problems_solutions(problem_id, solution_id, similarity_score)
            SELECT
              {pid}               AS problem_id,
              vs.solution_id      AS solution_id,
              1.0 - distance      AS similarity_score
            FROM vec_solutions AS vs, target
            WHERE vs.embedding
                  MATCH target.embedding
                AND k = {k};
            """
            cur.executescript(sql)
            self.conn.commit()

            cur.execute(
                "SELECT solution_id, similarity_score FROM problems_solutions WHERE problem_id = ? ORDER BY similarity_score DESC LIMIT ?",
                (pid, k)
            )
            rows = cur.fetchall()
            matched_solution_ids.extend(r[0] for r in rows)

            cur.execute("UPDATE problems SET is_processed = 1 WHERE problem_id = ?;", (pid,))
            self.conn.commit()

        seen = set()
        unique_solution_ids = []
        for sid in matched_solution_ids:
            if sid not in seen:
                seen.add(sid)
                unique_solution_ids.append(sid)

        return unique_solution_ids

    def collect_project_ids_for_solutions(self, solution_ids: List[int], top_n: int = 5) -> List[int]:
        if not solution_ids:
            return []

        cur = self.conn.cursor()
        placeholders = ",".join("?" for _ in solution_ids)
        query = f"""
          SELECT
            project_id,
            MAX(similarity_score) as score
          FROM projects_solutions
          WHERE solution_id IN ({placeholders})
          GROUP BY project_id
          ORDER BY score DESC
          LIMIT {top_n};
        """
        cur.execute(query, solution_ids)
        rows = cur.fetchall()

        return [row[0] for row in rows]

    def get_recommended_projects(self, problem_ids: List[int], top_n: int) -> List[Tuple[str, str, str, str]]:
        if not problem_ids:
            return []
        try:
            cur = self.conn.cursor()
            problem_placeholders = ",".join("?" for _ in problem_ids)
            query = f"""
                SELECT
                    p.project_id,
                    p.name,
                    p.description,
                    p.website,
                    p.contact_email,
                    MAX(psol.similarity_score * ps.similarity_score) as combined_similarity
                FROM
                    projects p
                JOIN
                    projects_solutions ps ON p.project_id = ps.project_id
                JOIN
                    problems_solutions psol ON ps.solution_id = psol.solution_id
                WHERE
                    psol.problem_id IN ({problem_placeholders})
                GROUP BY
                    p.project_id
                ORDER BY
                    combined_similarity DESC
                LIMIT ?;
            """
            params = tuple(problem_ids) + (top_n,)
            cur.execute(query, params)
            return cur.fetchall()
        except sqlite3.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_recommended_projects(self, problem_ids: List[int], top_n: int) -> List[Tuple[str, str, str, str]]:
        if not problem_ids:
            return []
        try:
            cur = self.conn.cursor()
            problem_placeholders = ",".join("?" for _ in problem_ids)
            query = f"""
                SELECT
                    p.project_id,
                    p.name,
                    p.description,
                    p.website,
                    p.contact_email,
                    MAX(psol.similarity_score * ps.similarity_score) as combined_similarity
                FROM
                    projects p
                JOIN
                    projects_solutions ps ON p.project_id = ps.project_id
                JOIN
                    problems_solutions psol ON ps.solution_id = psol.solution_id
                WHERE
                    psol.problem_id IN ({problem_placeholders})
                GROUP BY
                    p.project_id
                ORDER BY
                    combined_similarity DESC
                LIMIT ?;
            """
            params = tuple(problem_ids) + (top_n,)
            cur.execute(query, params)
            return cur.fetchall()
        except sqlite3.Error as e:
            logger.error("DB query failed: %s", e)
            return []

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