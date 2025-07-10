import psycopg2
import logging
import os
from typing import List, Tuple
import psycopg2
from langchain_community.embeddings import OpenAIEmbeddings

logger = logging.getLogger(__name__)

VECTOR_DIM = 1536


class Database:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = psycopg2.connect(
            dbname=os.environ.get("POSTGRES_DB"),
            user=os.environ.get("POSTGRES_USER"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            host=os.environ.get("POSTGRES_HOST"),
            port=os.environ.get("POSTGRES_PORT")
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def add_message(self, user_id: int, user_username: str, chat_title: str | None, text: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO messages (user_id, user_username, chat_title, text) "
                "VALUES (%s, %s, %s, %s) RETURNING message_id",
                (user_id, user_username, chat_title, text)
            )
            message_id = cur.fetchone()[0]
            self.conn.commit()
            return message_id
        except psycopg2.Error as e:
            logger.error("DB insert failed: %s", e)
            return None

    def get_message_by_id(self, message_id: int) -> str | None:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT text FROM messages WHERE message_id = %s", (message_id,))
            row = cur.fetchone()
            return row[0] if row else None
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return None

    def upsert_problem(self, name: str, context: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT problem_id FROM problems WHERE name=%s AND context=%s LIMIT 1",
                (name, context)
            )
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO problems (name, context) VALUES (%s, %s) RETURNING problem_id",
                (name, context)
            )
            problem_id = cur.fetchone()[0]
            self.conn.commit()
            return problem_id
        except psycopg2.Error as e:
            logger.error("DB upsert failed: %s", e)
            return None

    def upsert_solution(self, name: str, context: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT solution_id FROM solutions WHERE name=%s AND context=%s LIMIT 1",
                (name, context)
            )
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO solutions (name, context) VALUES (%s, %s) RETURNING solution_id",
                (name, context)
            )
            solution_id = cur.fetchone()[0]
            self.conn.commit()
            return solution_id
        except psycopg2.Error as e:
            logger.error("DB upsert failed: %s", e)
            return None

    def embed_new_solutions_and_projects(self, embedder: OpenAIEmbeddings) -> Tuple[List[int], List[int]]:
        cur = self.conn.cursor()

        # --- Solutions ---
        cur.execute("SELECT solution_id FROM solutions;")
        all_solution_ids = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT solution_id FROM vec_solutions;")
        embedded_solution_ids = {row[0] for row in cur.fetchall()}
        new_solution_ids = list(all_solution_ids - embedded_solution_ids)

        if new_solution_ids:
            placeholders = ",".join("%s" for _ in new_solution_ids)
            cur.execute(f"SELECT solution_id, context FROM solutions WHERE solution_id IN ({placeholders})",
                        new_solution_ids)
            rows_to_embed = cur.fetchall()
            for sid, context in rows_to_embed:
                if not context:
                    continue
                vec = embedder.embed_documents([context])[0]
                cur.execute(
                    "INSERT INTO vec_solutions(solution_id, embedding) VALUES (%s, %s) ON CONFLICT (solution_id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                    (sid, vec))
            self.conn.commit()

        # --- Projects ---
        cur.execute("SELECT project_id FROM projects;")
        all_project_ids = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT project_id FROM vec_projects;")
        embedded_project_ids = {row[0] for row in cur.fetchall()}
        new_project_ids = list(all_project_ids - embedded_project_ids)

        if new_project_ids:
            placeholders = ",".join("%s" for _ in new_project_ids)
            cur.execute(f"SELECT project_id, description FROM projects WHERE project_id IN ({placeholders})",
                        new_project_ids)
            rows_to_embed = cur.fetchall()
            for pid, desc in rows_to_embed:
                if not desc:
                    continue
                vec = embedder.embed_documents([desc])[0]
                cur.execute(
                    "INSERT INTO vec_projects(project_id, embedding) VALUES (%s, %s) ON CONFLICT (project_id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                    (pid, vec))
            self.conn.commit()

        return new_solution_ids, new_project_ids

    def match_new_solutions_to_projects(self, new_solution_ids: List[int], k_proj: int = 5):
        if not new_solution_ids:
            return

        cur = self.conn.cursor()
        for sid in new_solution_ids:
            cur.execute("SELECT embedding FROM vec_solutions WHERE solution_id = %s", (sid,))
            target_embedding = cur.fetchone()[0]

            cur.execute(
                """
                SELECT project_id, 1 - (embedding <=> %s) as similarity
                FROM vec_projects
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (target_embedding, k_proj)
            )
            matches = cur.fetchall()

            for project_id, similarity_score in matches:
                cur.execute(
                    "INSERT INTO projects_solutions(project_id, solution_id, similarity_score) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (project_id, sid, similarity_score)
                )
        self.conn.commit()

    def embed_and_match_new_problems(self, embedder: OpenAIEmbeddings, problem_ids: List[int], k: int = 5) -> \
            List[int]:
        cur = self.conn.cursor()
        matched_solution_ids = []

        for pid in problem_ids:
            cur.execute("SELECT context FROM problems WHERE problem_id = %s", (pid,))
            row = cur.fetchone()
            if row is None:
                continue
            problem_text = row[0]

            vec = embedder.embed_documents([problem_text])[0]
            cur.execute(
                "INSERT INTO vec_problems(problem_id, embedding) VALUES (%s, %s) ON CONFLICT (problem_id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                (pid, vec)
            )
            self.conn.commit()

            cur.execute(
                """
                INSERT INTO problems_solutions(problem_id, solution_id, similarity_score)
                SELECT %s, solution_id, 1 - (embedding <=> %s)
                FROM vec_solutions
                ORDER BY embedding <=> %s
                LIMIT %s
                ON CONFLICT DO NOTHING
                """,
                (pid, vec, vec, k)
            )
            self.conn.commit()

            cur.execute(
                "SELECT solution_id, similarity_score FROM problems_solutions WHERE problem_id = %s ORDER BY similarity_score DESC LIMIT %s",
                (pid, k)
            )
            rows = cur.fetchall()
            matched_solution_ids.extend(r[0] for r in rows)

            cur.execute("UPDATE problems SET is_processed = TRUE WHERE problem_id = %s;", (pid,))
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
        placeholders = ",".join("%s" for _ in solution_ids)
        query = f"""
          SELECT
            project_id,
            MAX(similarity_score) as score
          FROM projects_solutions
          WHERE solution_id IN ({placeholders})
          GROUP BY project_id
          ORDER BY score DESC
          LIMIT %s;
        """
        cur.execute(query, solution_ids + [top_n])
        rows = cur.fetchall()

        return [row[0] for row in rows]

    def get_problems_by_ids(self, problem_ids: List[int]) -> List[Tuple[str, str]]:
        if not problem_ids:
            return []
        try:
            cur = self.conn.cursor()
            placeholders = ",".join("%s" for _ in problem_ids)
            query = f"SELECT name, context FROM problems WHERE problem_id IN ({placeholders})"
            cur.execute(query, tuple(problem_ids))
            return cur.fetchall()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_projects_by_ids(self, project_ids: List[int], top_n: int) -> List[Tuple[str, str, str, str]]:
        if not project_ids:
            return []
        try:
            cur = self.conn.cursor()
            selected_ids = project_ids[:top_n]
            placeholders = ",".join("%s" for _ in selected_ids)
            query = (
                f"SELECT name, description, website, contact_email "
                f"FROM projects WHERE project_id IN ({placeholders})"
            )
            cur.execute(query, tuple(selected_ids))
            return cur.fetchall()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def add_response(self, message_id: int, text: str):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO responses(message_id, text) VALUES (%s, %s)",
                (message_id, text)
            )
            self.conn.commit()
        except psycopg2.Error as e:
            logger.error("DB insert failed: %s", e)

    def create_project(self, name: str, description: str | None, website: str | None,
                       contact_email: str | None) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO projects (name, description, website, contact_email) VALUES (%s, %s, %s, %s) RETURNING project_id",
                (name, description, website, contact_email)
            )
            project_id = cur.fetchone()[0]
            self.conn.commit()
            return project_id
        except psycopg2.Error as e:
            logger.error("DB insert failed: %s", e)
            return None

    def get_projects(self) -> List[Tuple[int, str, str, str, str, str]]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT project_id, name, description, created_at, website, contact_email FROM projects")
            return cur.fetchall()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_project_by_id(self, project_id: int) -> Tuple[int, str, str, str, str, str] | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT project_id, name, description, created_at, website, contact_email FROM projects WHERE project_id = %s",
                (project_id,))
            return cur.fetchone()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return None

    def update_project(self, project_id: int, name: str | None, description: str | None, website: str | None,
                       contact_email: str | None) -> bool:
        try:
            cur = self.conn.cursor()

            fields = []
            values = []
            if name is not None:
                fields.append("name = %s")
                values.append(name)
            if description is not None:
                fields.append("description = %s")
                values.append(description)
            if website is not None:
                fields.append("website = %s")
                values.append(website)
            if contact_email is not None:
                fields.append("contact_email = %s")
                values.append(contact_email)

            if not fields:
                return False

            values.append(project_id)

            cur.execute(
                f"UPDATE projects SET {', '.join(fields)} WHERE project_id = %s",
                tuple(values)
            )
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB update failed: %s", e)
            return False

    def delete_project(self, project_id: int) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB delete failed: %s", e)
            return False

    def create_problem(self, name: str, context: str | None) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO problems (name, context) VALUES (%s, %s) RETURNING problem_id",
                (name, context)
            )
            problem_id = cur.fetchone()[0]
            self.conn.commit()
            return problem_id
        except psycopg2.Error as e:
            logger.error("DB insert failed: %s", e)
            return None

    def get_problems(self) -> List[Tuple[int, str, str, str, bool]]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT problem_id, name, context, created_at, is_processed FROM problems")
            return cur.fetchall()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_problem_by_id(self, problem_id: int) -> Tuple[int, str, str, str, bool] | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT problem_id, name, context, created_at, is_processed FROM problems WHERE problem_id = %s",
                (problem_id,))
            return cur.fetchone()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return None

    def update_problem(self, problem_id: int, name: str | None, context: str | None,
                       is_processed: bool | None) -> bool:
        try:
            cur = self.conn.cursor()
            fields = []
            values = []
            if name is not None:
                fields.append("name = %s")
                values.append(name)
            if context is not None:
                fields.append("context = %s")
                values.append(context)
            if is_processed is not None:
                fields.append("is_processed = %s")
                values.append(is_processed)

            if not fields:
                return False

            values.append(problem_id)

            cur.execute(
                f"UPDATE problems SET {', '.join(fields)} WHERE problem_id = %s",
                tuple(values)
            )
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB update failed: %s", e)
            return False

    def delete_problem(self, problem_id: int) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM problems WHERE problem_id = %s", (problem_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB delete failed: %s", e)
            return False

    def create_solution(self, name: str, context: str | None) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO solutions (name, context) VALUES (%s, %s) RETURNING solution_id",
                (name, context)
            )
            solution_id = cur.fetchone()[0]
            self.conn.commit()
            return solution_id
        except psycopg2.Error as e:
            logger.error("DB insert failed: %s", e)
            return None

    def get_solutions(self) -> List[Tuple[int, str, str, str]]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT solution_id, name, context, created_at FROM solutions")
            return cur.fetchall()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_solution_by_id(self, solution_id: int) -> Tuple[int, str, str, str] | None:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT solution_id, name, context, created_at FROM solutions WHERE solution_id = %s",
                        (solution_id,))
            return cur.fetchone()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return None

    def update_solution(self, solution_id: int, name: str | None, context: str | None) -> bool:
        try:
            cur = self.conn.cursor()
            fields = []
            values = []
            if name is not None:
                fields.append("name = %s")
                values.append(name)
            if context is not None:
                fields.append("context = %s")
                values.append(context)

            if not fields:
                return False

            values.append(solution_id)

            cur.execute(
                f"UPDATE solutions SET {', '.join(fields)} WHERE solution_id = %s",
                tuple(values)
            )
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB update failed: %s", e)
            return False

    def delete_solution(self, solution_id: int) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM solutions WHERE solution_id = %s", (solution_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB delete failed: %s", e)
            return False

    def create_organization(self, name: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO organizations (name) VALUES (%s) RETURNING id",
                (name,)
            )
            organization_id = cur.fetchone()[0]
            self.conn.commit()
            return organization_id
        except psycopg2.Error as e:
            logger.error("DB insert failed: %s", e)
            return None

    def get_organizations(self) -> List[Tuple[int, str]]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, name FROM organizations")
            return cur.fetchall()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return []

    def get_organization_by_id(self, organization_id: int) -> Tuple[int, str] | None:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, name FROM organizations WHERE id = %s", (organization_id,))
            return cur.fetchone()
        except psycopg2.Error as e:
            logger.error("DB query failed: %s", e)
            return None

    def update_organization(self, organization_id: int, name: str) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE organizations SET name = %s WHERE id = %s",
                (name, organization_id)
            )
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB update failed: %s", e)
            return False

    def delete_organization(self, organization_id: int) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM organizations WHERE id = %s", (organization_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error("DB delete failed: %s", e)
            return False