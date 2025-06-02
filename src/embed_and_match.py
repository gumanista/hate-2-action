# src/embed_and_match.py

import os
import sqlite3
import sqlite_vec
import openai
from typing import Tuple, List

# Constants
DIM = 1536
EMBEDDING_MODEL = "text-embedding-3-small"
K = 5  # Default number of neighbors to fetch

def generate_embedding(text: str) -> list:
    """
    Generate an embedding for the given text using OpenAI's Embeddings API.
    Returns a list of DIM floats.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    resp = openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
    emb = resp.data[0].embedding
    if len(emb) != DIM:
        raise ValueError(f"Unexpected embedding size: got {len(emb)}, expected {DIM}")
    return emb

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
    # ─── Problems ─────────────────
    cur.execute("SELECT problem_id FROM problems_embeddings;")
    existing_p = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT problem_id, context FROM problems;")
    for pid, ctx in cur:
        if pid in existing_p:
            continue
        blob = sqlite_vec.serialize_float32(generate_embedding(ctx or ""))
        cur.execute(
            "INSERT INTO problems_embeddings(problem_id, embedding) VALUES (?, ?)",
            (pid, blob),
        )
    conn.commit()

    # ─── Solutions ─────────────────
    cur.execute("SELECT solution_id FROM solutions_embeddings;")
    existing_s = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT solution_id, context FROM solutions;")
    for sid, ctx in cur:
        if sid in existing_s:
            continue
        blob = sqlite_vec.serialize_float32(generate_embedding(ctx or ""))
        cur.execute(
            "INSERT INTO solutions_embeddings(solution_id, embedding) VALUES (?, ?)",
            (sid, blob),
        )
    conn.commit()

    # ─── Projects ─────────────────
    cur.execute("SELECT project_id FROM projects_embeddings;")
    existing_pr = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT project_id, description FROM projects;")
    for prid, desc in cur:
        if prid in existing_pr:
            continue
        blob = sqlite_vec.serialize_float32(generate_embedding(desc or ""))
        cur.execute(
            "INSERT INTO projects_embeddings(project_id, embedding) VALUES (?, ?)",
            (prid, blob),
        )
    conn.commit()

def compute_similarities(
    conn: sqlite3.Connection,
    problem_ids: List[int],
    k: int = K
) -> Tuple[List[int], List[int]]:
    """
    For the given list of problem_ids:
      1) Find top-k nearest solutions per problem,
      2) Aggregate matches, keep best similarity per solution,
      3) Select top-k solutions overall,
      4) For each selected solution, find top-k nearest projects,
      5) Aggregate matches, keep best similarity per project,
      6) Select top-k projects overall.

    Inserts all problem-solution and project-solution pairs into their respective tables,
    and returns (solution_ids_top_k, project_ids_top_k).
    """
    cur = conn.cursor()
    # Clear previous matches
    cur.execute("DELETE FROM problems_solutions;")
    cur.execute("DELETE FROM projects_solutions;")
    conn.commit()

    # 1) Problems → Solutions
    problem_solution_matches: List[tuple[int, int, float]] = []
    for pid in problem_ids:
        # Fetch the embedding for this problem_id
        cur.execute(
            "SELECT embedding FROM problems_embeddings WHERE problem_id = ?",
            (pid,)
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            # No embedding for this problem, skip
            continue
        problem_blob = row[0]
        # Now query the nearest solutions using that blob
        cur.execute("""
            SELECT solution_id, distance AS similarity_score
            FROM solutions_embeddings
            WHERE embedding MATCH ?
            AND k = ?
        """, (problem_blob, k))
        matches = cur.fetchall()  # list of (solution_id, similarity_score)
        if not matches:
            continue
        # Insert into problems_solutions
        cur.executemany(
            "INSERT INTO problems_solutions(problem_id, solution_id, similarity_score) VALUES (?, ?, ?);",
            ((pid, sid, dist) for sid, dist in matches)
        )
        for sid, dist in matches:
            problem_solution_matches.append((pid, sid, dist))

    conn.commit()

    # 2) Aggregate best similarity per solution
    best_score_per_solution: dict[int, float] = {}
    for _, sid, dist in problem_solution_matches:
        if sid not in best_score_per_solution or dist < best_score_per_solution[sid]:
            best_score_per_solution[sid] = dist

    # 3) Select top-k solutions by best (lowest) distance
    sorted_solutions = sorted(best_score_per_solution.items(), key=lambda x: x[1])
    top_solutions = [sid for sid, _ in sorted_solutions[:k]]

    # 4) Solutions → Projects
    project_solution_matches: List[tuple[int, int, float]] = []
    for sid in top_solutions:
        # Fetch the embedding for this solution_id
        cur.execute(
            "SELECT embedding FROM solutions_embeddings WHERE solution_id = ?",
            (sid,)
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            continue
        solution_blob = row[0]
        # Now query nearest projects using that blob
        cur.execute("""
            SELECT project_id, distance AS similarity_score
            FROM projects_embeddings
            WHERE embedding MATCH ?
            AND k = ?
        """, (solution_blob, k))
        proj_matches = cur.fetchall()  # list of (project_id, similarity_score)
        if not proj_matches:
            continue
        # Insert into projects_solutions
        cur.executemany(
            "INSERT INTO projects_solutions(project_id, solution_id, similarity_score) VALUES (?, ?, ?);",
            ((proj_id, sid, dist) for proj_id, dist in proj_matches)
        )
        for proj_id, dist in proj_matches:
            project_solution_matches.append((sid, proj_id, dist))

    conn.commit()

    # 5) Aggregate best similarity per project
    best_score_per_project: dict[int, float] = {}
    for _, proj_id, dist in project_solution_matches:
        if proj_id not in best_score_per_project or dist < best_score_per_project[proj_id]:
            best_score_per_project[proj_id] = dist

    # 6) Select top-k projects by best (lowest) distance
    sorted_projects = sorted(best_score_per_project.items(), key=lambda x: x[1])
    top_projects = [proj_id for proj_id, _ in sorted_projects[:k]]

    return top_solutions, top_projects

def match_embeddings(
    db_file: str,
    problem_ids: List[int],
    k: int = K
) -> Tuple[List[int], List[int]]:
    """
    Connect to the database, create & populate embedding tables,
    run similarity search using only the given problem_ids, and return
    (top_solution_ids, top_project_ids).
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    conn = sqlite3.connect(db_file)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    create_vec_tables(conn)
    populate_embeddings(conn)

    if not problem_ids:
        # No detected problems → no matches
        return [], []

    solution_ids, project_ids = compute_similarities(conn, problem_ids, k)
    conn.close()
    return solution_ids, project_ids

if __name__ == "__main__":
    DB_PATH = os.getenv("DB_PATH", "donation.db")
    print(f"Running embedding and matching process for database: {DB_PATH}")
    try:
        sol_ids, proj_ids = match_embeddings(DB_PATH, [1, 2, 3], k=K)
        print(f"Matched solutions: {sol_ids}")
        print(f"Matched projects:  {proj_ids}")
    except Exception as e:
        print(f"Error: {e}")
