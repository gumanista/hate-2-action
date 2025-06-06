# src/embed_and_match.py

import sqlite3
import json
import os
from typing import List, Tuple

from langchain_community.embeddings import OpenAIEmbeddings

VECTOR_DIM = 1536  # Embedding dimension size for OpenAI embeddings

def _load_vec0_extension(conn):
    # Load the installed sqlite-vec package
    import sqlite_vec
    sqlite_vec.load(conn)


def _create_vec_tables_if_missing(conn: sqlite3.Connection):
    """
    Creates the three vec0 virtual tables if they don't already exist:
      • vec_solutions  (solution_id INTEGER PRIMARY KEY, embedding float[VECTOR_DIM])
      • vec_projects   (project_id INTEGER PRIMARY KEY, embedding float[VECTOR_DIM])
      • vec_problems   (problem_id  INTEGER PRIMARY KEY, embedding float[VECTOR_DIM])
    """
    cur = conn.cursor()

    # Create tables for vec_solutions, vec_projects, and vec_problems
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

    conn.commit()


def _populate_solutions_and_projects(conn: sqlite3.Connection, embedder: OpenAIEmbeddings):
    """
    On the first run, compute embeddings for *all* rows in `solutions` and `projects`,
    and insert them into vec_solutions / vec_projects.
    """
    cur = conn.cursor()

    # Populate vec_solutions if empty
    cur.execute("SELECT COUNT(*) FROM vec_solutions;")
    count_vs = cur.fetchone()[0]
    if count_vs == 0:
        cur.execute("SELECT solution_id, context FROM solutions;")
        rows = cur.fetchall()
        for solution_id, context_text in rows:
            vec = embedder.embed_documents([context_text])[0]
            cur.execute(
                "INSERT OR REPLACE INTO vec_solutions(solution_id, embedding) VALUES (?, json(?));",
                (solution_id, json.dumps(vec))
            )
        conn.commit()

    # Populate vec_projects if empty
    cur.execute("SELECT COUNT(*) FROM vec_projects;")
    count_vp = cur.fetchone()[0]
    if count_vp == 0:
        cur.execute("SELECT project_id, description FROM projects;")
        rows = cur.fetchall()
        for project_id, description_text in rows:
            vec = embedder.embed_documents([description_text])[0]
            cur.execute(
                "INSERT OR REPLACE INTO vec_projects(project_id, embedding) VALUES (?, json(?));",
                (project_id, json.dumps(vec))
            )
        conn.commit()


def _populate_projects_solutions(conn: sqlite3.Connection, k_proj: int = 5):
    """
    On the first run (or whenever projects_solutions is empty), match *every* solution
    to its top-k_proj projects and insert into projects_solutions.
    """
    cur = conn.cursor()

    # Check if projects_solutions is already populated
    cur.execute("SELECT COUNT(*) FROM projects_solutions;")
    count_ps = cur.fetchone()[0]
    if count_ps == 0:
        # Fetch all solution_ids
        cur.execute("SELECT solution_id FROM solutions;")
        all_solutions = [row[0] for row in cur.fetchall()]

        for sid in all_solutions:
            sql = f"""
            WITH target AS (
              SELECT embedding
              FROM vec_solutions
              WHERE solution_id = {sid}
            )
            INSERT OR IGNORE INTO projects_solutions(project_id, solution_id, similarity_score)
            SELECT
              vp.project_id       AS project_id,
              {sid}               AS solution_id,
              1.0 - distance      AS similarity_score
            FROM vec_projects AS vp, target
            WHERE vp.embedding
                  MATCH target.embedding
                AND k = {k_proj};
            """
            cur.executescript(sql)

        conn.commit()


def _embed_and_match_new_problems(
    conn: sqlite3.Connection,
    embedder: OpenAIEmbeddings,
    problem_ids: List[int],
    k: int = 5  # Top 5 solutions to match
) -> List[int]:
    """
    For each problem_id in problem_ids (all of which should have is_processed = 0),
    1) Compute its embedding, insert into vec_problems.
    2) Run a vec0 KNN query (k nearest solutions), insert into problems_solutions.
    Returns a flat list of *all* solution_ids matched to these problems.
    """
    cur = conn.cursor()
    matched_solution_ids = []

    for pid in problem_ids:
        # Fetch the problem text
        cur.execute("SELECT context FROM problems WHERE problem_id = ?", (pid,))
        row = cur.fetchone()
        if row is None:
            continue
        problem_text = row[0]

        # Embed and insert into vec_problems
        vec = embedder.embed_documents([problem_text])[0]
        cur.execute(
            "INSERT OR REPLACE INTO vec_problems(problem_id, embedding) VALUES (?, json(?));",
            (pid, json.dumps(vec))
        )
        conn.commit()

        # KNN query: “problem” → top k “solutions”
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
            AND k = {k};  -- Select top k solutions
        """
        cur.executescript(sql)
        conn.commit()

        # Collect top k solution_ids
        cur.execute(
            "SELECT solution_id FROM problems_solutions WHERE problem_id = ? ORDER BY similarity_score DESC LIMIT ?",
            (pid, k)
        )
        rows = cur.fetchall()
        matched_solution_ids.extend(r[0] for r in rows)

        # Mark problem as processed
        cur.execute("UPDATE problems SET is_processed = 1 WHERE problem_id = ?;", (pid,))
        conn.commit()

    # Deduplicate while preserving order
    seen = set()
    unique_solution_ids = []
    for sid in matched_solution_ids:
        if sid not in seen:
            seen.add(sid)
            unique_solution_ids.append(sid)

    return unique_solution_ids


def _collect_project_ids_for_solutions(
    conn: sqlite3.Connection,
    solution_ids: List[int],
    top_n: int = 5  # Top 5 projects
) -> List[int]:
    if not solution_ids:
        return []

    cur = conn.cursor()
    placeholders = ",".join("?" for _ in solution_ids)

    # Fetch all matching rows, ordered by similarity_score DESC
    query = f"""
      SELECT project_id
      FROM projects_solutions
      WHERE solution_id IN ({placeholders})
      ORDER BY similarity_score DESC
      LIMIT {top_n};  -- Select top n projects
    """
    cur.execute(query, solution_ids)
    rows = cur.fetchall()

    seen = set()
    unique_project_ids = []
    for (pid,) in rows:
        if pid not in seen:
            seen.add(pid)
            unique_project_ids.append(pid)

    return unique_project_ids


def match_embeddings(
    db_path: str,
    problem_ids: List[int],
    k: int = 5  # Top 5 solutions and projects
) -> Tuple[List[int], List[int]]:
    """
    1) Connect to SQLite, load vec0.
    2) Create vec_solutions / vec_projects / vec_problems (if missing).
    3) On the first run, embed + insert *all* solutions and projects, then populate projects_solutions.
    4) For each new problem_id, embed + KNN-match against solutions → populate problems_solutions.
    5) Return (sol_ids, proj_ids):
         • sol_ids = all solution_ids matched to the given problem_ids (deduped, in descending similarity order).
         • proj_ids = all project_ids matched to those solution_ids (deduped, in descending similarity order).
    """
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    _load_vec0_extension(conn)
    conn.enable_load_extension(False)

    # Create the necessary tables if missing
    _create_vec_tables_if_missing(conn)

    # Initialize the embedding model
    embedder = OpenAIEmbeddings()

    # First-run: populate all solution/project embeddings if needed
    _populate_solutions_and_projects(conn, embedder)

    # First-run: populate projects_solutions if needed
    _populate_projects_solutions(conn, k_proj=3)

    # For each newly detected problem, embed & match → solutions
    sol_ids = _embed_and_match_new_problems(conn, embedder, problem_ids, k)

    # Collect all matching project_ids for the selected solutions
    proj_ids = _collect_project_ids_for_solutions(conn, sol_ids, top_n=k)

    conn.close()
    return sol_ids, proj_ids

