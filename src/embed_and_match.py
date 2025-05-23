import os
import sqlite3
import sqlite_vec
import openai
from typing import Tuple, List

# Constants from embed_match.py:
DIM = 1536
EMBEDDING_MODEL = "text-embedding-3-small"
K = 10 # Default number of neighbors to fetch

def generate_embedding(text: str) -> list:
    """
    Generate an embedding for the given text using OpenAI's Embeddings API (v1.0+).
    Returns a list of floats of length DIM.
    """
    # Initialize OpenAI key here as well, in case generate_embedding is called independently
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    response = openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    # Access the first embedding via attribute
    embedding = response.data[0].embedding
    if len(embedding) != DIM:
        raise ValueError(f"Unexpected embedding size: got {len(embedding)}, expected {DIM}")
    return embedding

def create_vec_tables(conn: sqlite3.Connection, dim: int = DIM):
    cur = conn.cursor()
    cur.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS problems_embeddings
    USING vec0(
      problem_id INTEGER PRIMARY KEY,
      embedding  FLOAT[{dim}]
    );
    """)
    cur.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS solutions_embeddings
    USING vec0(
      solution_id INTEGER PRIMARY KEY,
      embedding    FLOAT[{dim}]
    );
    """)
    cur.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS projects_embeddings
    USING vec0(
      project_id INTEGER PRIMARY KEY,
      embedding   FLOAT[{dim}]
    );
    """)
    conn.commit()


def populate_embeddings(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # ─── Problems: only embed new ones ────────────────────────────────────────
    cur.execute("SELECT problem_id FROM problems_embeddings;")
    existing_p = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT problem_id, context FROM problems;")
    for pid, ctx in cur:
        if pid in existing_p:
            continue
        emb = generate_embedding(ctx or "")
        blob = sqlite_vec.serialize_float32(emb)
        cur.execute(
            "INSERT INTO problems_embeddings(problem_id, embedding) VALUES (?, ?)",
            (pid, blob),
        )
    conn.commit()

    # ─── Solutions: only embed new ones ──────────────────────────────────────
    cur.execute("SELECT solution_id FROM solutions_embeddings;")
    existing_s = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT solution_id, context FROM solutions;")
    for sid, ctx in cur:
        if sid in existing_s:
            continue
        emb = generate_embedding(ctx or "")
        blob = sqlite_vec.serialize_float32(emb)
        cur.execute(
            "INSERT INTO solutions_embeddings(solution_id, embedding) VALUES (?, ?)",
            (sid, blob),
        )
    conn.commit()

    # ─── Projects: only embed new ones ───────────────────────────────────────
    cur.execute("SELECT project_id FROM projects_embeddings;")
    existing_pr = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT project_id, description FROM projects;")
    for prid, desc in cur:
        if prid in existing_pr:
            continue
        emb = generate_embedding(desc or "")
        blob = sqlite_vec.serialize_float32(emb)
        cur.execute(
            "INSERT INTO projects_embeddings(project_id, embedding) VALUES (?, ?)",
            (prid, blob),
        )
    conn.commit()



def compute_similarities(conn: sqlite3.Connection, k: int = K) -> Tuple[List[int], List[int]]:
    """
    Run KNN searches to fill the problems_solutions and projects_solutions tables.
    Collect and return the solution_ids matched to problems and projects.
    """
    cur = conn.cursor()
    # Clear existing matches
    cur.execute("DELETE FROM problems_solutions;")
    cur.execute("DELETE FROM projects_solutions;")
    conn.commit()

    problem_solution_ids = set()
    project_solution_ids = set()

    # Problems -> Solutions
    cur.execute("SELECT problem_id FROM problems_embeddings;")
    for (pid,) in cur.fetchall():
        cur.execute(
            """
            SELECT solution_id AS solution_id, distance AS similarity_score
            FROM solutions_embeddings
            WHERE embedding MATCH (
                SELECT embedding FROM problems_embeddings WHERE problem_id = ?
            )
            AND k = ?;
            """, (pid, k)
        )
        matches = cur.fetchall()
        cur.executemany(
            "INSERT INTO problems_solutions(problem_id, solution_id, similarity_score) VALUES (?, ?, ?);",
            ((pid, sid, dist) for sid, dist in matches)
        )
        for sid, _ in matches:
            problem_solution_ids.add(sid)


    # Projects -> Solutions
    cur.execute("SELECT project_id FROM projects_embeddings;")
    for (proj_id,) in cur.fetchall():
        cur.execute(
            """
            SELECT solution_id AS solution_id, distance AS similarity_score
            FROM solutions_embeddings
            WHERE embedding MATCH (
                SELECT embedding FROM projects_embeddings WHERE project_id = ?
            )
            AND k = ?;
            """, (proj_id, k)
        )
        matches = cur.fetchall()
        cur.executemany(
            "INSERT INTO projects_solutions(project_id, solution_id, similarity_score) VALUES (?, ?, ?);",
            ((proj_id, sid, dist) for sid, dist in matches)
        )
        for sid, _ in matches:
            project_solution_ids.add(sid)

    conn.commit()
    return sorted(list(problem_solution_ids)), sorted(list(project_solution_ids))


def match_embeddings(db_file: str, k: int = 10) -> Tuple[List[int], List[int]]:
    conn = sqlite3.connect(db_file)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # ensure tables exist
    from src.embed_and_match import create_vec_tables
    create_vec_tables(conn)

    # populate only new embeddings
    populate_embeddings(conn)

    solution_ids, project_ids = compute_similarities(conn, k)
    conn.close()
    return solution_ids, project_ids





if __name__ == "__main__":
    # Example usage (similar to original main, but calls the new function)
    DB_PATH = os.getenv("DB_PATH", "donation.db")
    print(f"Running embedding and matching process for database: {DB_PATH}")
    try:
        matched_solution_ids, matched_project_ids = match_embeddings(DB_PATH)
        print(f"Matched solution IDs for problems: {matched_solution_ids}")
        print(f"Matched solution IDs for projects: {matched_project_ids}")
    except RuntimeError as e:
        print(f"Error: {e}")